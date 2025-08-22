
const { MptcpKernel } = require('../meshadmin-pathways/packages/mptcp-kernel/src/index.js');

class PythonBridge {
    constructor() {
        this.kernel = new MptcpKernel({
            endpoint: 'localhost',
            port: 9090,
            secure: false
        });
    }

    async execute(command, args = []) {
        try {
            await this.kernel.connect();
            
            let result;
            switch (command) {
                case 'healthCheck':
                    result = await this.kernel.healthCheck();
                    break;
                case 'getSystemOverview':
                    const overview = await this.kernel.getStats();
                    const connections = await this.kernel.listConnections();
                    result = { overview, connections };
                    break;
                case 'listConnections':
                    result = await this.kernel.listConnections();
                    break;
                case 'getPathStatistics':
                    result = await this.kernel.getTopology();
                    break;
                case 'getPerformanceMetrics':
                    result = await this.kernel.getStats();
                    break;
                default:
                    throw new Error(`Unknown command: ${command}`);
            }
            
            return { success: true, data: result };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
}

// Command line interface
if (require.main === module) {
    const bridge = new PythonBridge();
    const command = process.argv[2];
    const args = process.argv.slice(3);
    
    bridge.execute(command, args).then(result => {
        console.log(JSON.stringify(result));
        process.exit(0);
    }).catch(error => {
        console.log(JSON.stringify({ success: false, error: error.message }));
        process.exit(1);
    });
}

module.exports = PythonBridge;
