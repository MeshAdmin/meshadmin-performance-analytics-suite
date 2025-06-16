package main

import (
    "context"
    "fmt"
    "io"
    "log"
    "math/rand"
    "net"
    "strconv"
    "strings"
    "sync"
    "time"

    "fyne.io/fyne/v2"
    "fyne.io/fyne/v2/app"
    "fyne.io/fyne/v2/container"
    "fyne.io/fyne/v2/widget"
)

// ConnectionInfo holds metadata for a single active connection
type ConnectionInfo struct {
    ID         string
    Source     string
    Destination string
    StartTime  time.Time
}

// LBManager manages the load balancer state
type LBManager struct {
    mu           sync.Mutex             // protects activeConns
    activeConns  []ConnectionInfo
    backends     []string
    backendIndex int

    cancelFunc   context.CancelFunc     // used to stop the listener goroutine
    running      bool
}

// AddConnection adds a connection record to the active list
func (m *LBManager) AddConnection(ci ConnectionInfo) {
    m.mu.Lock()
    defer m.mu.Unlock()
    m.activeConns = append(m.activeConns, ci)
}

// RemoveConnectionByID removes a connection by matching ID
func (m *LBManager) RemoveConnectionByID(id string) {
    m.mu.Lock()
    defer m.mu.Unlock()
    for i, c := range m.activeConns {
        if c.ID == id {
            // remove it
            m.activeConns = append(m.activeConns[:i], m.activeConns[i+1:]...)
            break
        }
    }
}

// ListConnections returns a snapshot of active connections
func (m *LBManager) ListConnections() []ConnectionInfo {
    m.mu.Lock()
    defer m.mu.Unlock()
    // return a copy
    copied := make([]ConnectionInfo, len(m.activeConns))
    copy(copied, m.activeConns)
    return copied
}

// pickBackend does a round-robin pick of a backend
func (m *LBManager) pickBackend() (string, string, error) {
    if len(m.backends) == 0 {
        return "", "", fmt.Errorf("no backends available")
    }
    backend := m.backends[m.backendIndex%len(m.backends)]
    m.backendIndex++
    parts := strings.Split(backend, ":")
    if len(parts) != 2 {
        return "", "", fmt.Errorf("invalid backend format: %s", backend)
    }
    return parts[0], parts[1], nil
}

// StartListener starts the load balancer in a background goroutine
func (m *LBManager) StartListener(listenPort int, backends []string) error {
    if m.running {
        return fmt.Errorf("already running")
    }

    m.backends = backends
    m.backendIndex = 0
    m.running = true

    ctx, cancel := context.WithCancel(context.Background())
    m.cancelFunc = cancel

    go func() {
        defer func() {
            m.running = false
        }()
								listener, err := net.ListenTCP("tcp", &net.TCPAddr{Port: listenPort})
								if err != nil {
								    log.Printf("Error listening on port %d: %v\n", listenPort, err)
								    return
								}
								defer listener.Close()

        log.Printf("Load balancer listening on port %d\n", listenPort)

        for {
            select {
            case <-ctx.Done():
                // stop signaled
                log.Println("Stopping load balancer...")
                return
            default:
            }

            // Accept new connections
            listener.SetDeadline(time.Now().Add(200 * time.Millisecond)) // short timeout so we can check ctx
            conn, err := listener.Accept()
            if err != nil {
                // check if it's a timeout or a real error
                netErr, ok := err.(net.Error)
                if ok && netErr.Timeout() {
                    // normal, keep looping
                    continue
                }
                log.Printf("Accept error: %v\n", err)
                continue
            }

            // We got a new client - handle in a goroutine
            go m.handleClient(ctx, conn)
        }
    }()
    return nil
}

// StopListener signals the load balancer to stop
func (m *LBManager) StopListener() {
    if m.cancelFunc != nil {
        m.cancelFunc() // signal the goroutine to stop
    }
    m.running = false
    log.Println("StopListener called")
}

// handleClient proxies traffic to the next backend
func (m *LBManager) handleClient(ctx context.Context, clientConn net.Conn) {
    defer clientConn.Close()

    host, port, err := m.pickBackend()
    if err != nil {
        log.Printf("Error picking backend: %v\n", err)
        return
    }

    backendConn, err := net.Dial("tcp", net.JoinHostPort(host, port))
    if err != nil {
        log.Printf("Error connecting to backend %s:%s => %v\n", host, port, err)
        return
    }
    defer backendConn.Close()

    // create connection record
    connID := fmt.Sprintf("%d", rand.Uint64())
    srcAddr := clientConn.RemoteAddr().String()
    dstAddr := net.JoinHostPort(host, port)

    ci := ConnectionInfo{
        ID:          connID,
        Source:      srcAddr,
        Destination: dstAddr,
        StartTime:   time.Now(),
    }
    m.AddConnection(ci)
    defer m.RemoveConnectionByID(connID)

    // copy data both ways
    // We'll do io.Copy in goroutines:
    done := make(chan struct{}, 2)

    go func() {
        defer func() { done <- struct{}{} }()
        _, _ = io.Copy(backendConn, clientConn)
    }()
    go func() {
        defer func() { done <- struct{}{} }()
        _, _ = io.Copy(clientConn, backendConn)
    }()

    // Wait for both directions to finish or context done
    select {
    case <-done:
    case <-done:
        // we read from the channel twice so this ensures both goroutines have ended
    case <-ctx.Done():
        // context canceled
    }
}

// ------------------------------------------------------------------------
// GUI / Fyne
// ------------------------------------------------------------------------

func main() {
    // create the Fyne application
    myApp := app.New()
    w := myApp.NewWindow("Go + Fyne Load Balancer")

    // manager that holds state
    manager := &LBManager{
        activeConns: make([]ConnectionInfo, 0),
    }
    rand.Seed(time.Now().UnixNano())

    // UI controls
    portEntry := widget.NewEntry()
    portEntry.SetText("8080")

    backendsEntry := widget.NewMultiLineEntry()
    backendsEntry.SetText("127.0.0.1:8081\n127.0.0.1:8082")

    statusLabel := widget.NewLabel("Status: Stopped")

    // We'll use a simple list to display active connections
    // Alternatively, you can use widget.NewTable, container.NewGrid, etc.
    list := widget.NewList(
        func() int {
            return len(manager.ListConnections())
        },
        func() fyne.CanvasObject {
            return widget.NewLabel("") // a template
        },
        func(i widget.ListItemID, o fyne.CanvasObject) {
            // update
            conns := manager.ListConnections()
            if i >= 0 && i < len(conns) {
                c := conns[i]
                o.(*widget.Label).SetText(
                    fmt.Sprintf("ID:%s | %s -> %s | %s",
                        c.ID, c.Source, c.Destination, c.StartTime.Format("15:04:05")),
                )
            }
        },
    )

    startBtn := widget.NewButton("Start", func() {
        portStr := portEntry.Text
        p, err := strconv.Atoi(portStr)
        if err != nil {
            statusLabel.SetText("Status: Invalid port")
            return
        }
        lines := strings.Split(backendsEntry.Text, "\n")
        var backends []string
        for _, ln := range lines {
            ln = strings.TrimSpace(ln)
            if ln != "" {
                backends = append(backends, ln)
            }
        }
        if len(backends) == 0 {
            statusLabel.SetText("Status: No backends provided")
            return
        }

        err = manager.StartListener(p, backends)
        if err != nil {
            statusLabel.SetText(fmt.Sprintf("Status: Error: %v", err))
            return
        }
        statusLabel.SetText(fmt.Sprintf("Status: Running on port %d", p))
    })

    stopBtn := widget.NewButton("Stop", func() {
        manager.StopListener()
        statusLabel.SetText("Status: Stopped")
    })

    // layout
    form := container.NewVBox(
        widget.NewLabel("Listen Port:"),
        portEntry,
        widget.NewLabel("Backend Servers (host:port, one per line):"),
        backendsEntry,
        container.NewHBox(startBtn, stopBtn),
        statusLabel,
        widget.NewLabel("Active Connections:"),
        list,
    )

    w.SetContent(form)
    w.Resize(fyne.NewSize(500, 500))

    // We'll set up a ticker to refresh the list
    go func() {
        ticker := time.NewTicker(1 * time.Second)
        for range ticker.C {
												if w.Content() == nil {
												    ticker.Stop()
												    return
												}
            // Refresh the list in the main UI thread
												list.Refresh()
        }
    }()

    w.ShowAndRun()
}