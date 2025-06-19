/**
 * Enhanced LLM Model Management with Real-time Feedback
 * 
 * This module provides real-time progress feedback for LLM model loading/unloading
 * operations using Server-Sent Events (SSE) with fallback to regular fetch.
 */

class LLMManager {
    constructor() {
        this.currentEventSource = null;
        this.loadingModelId = null;
        this.sseEnabled = true; // Feature flag for SSE
        this.progressBars = new Map(); // Track progress bars by model ID
        this.spinners = new Map(); // Track spinners by model ID
    }

    /**
     * Show loading spinner and disable model actions
     */
    showSpinner(modelId) {
        const modelCard = document.querySelector(`[data-model-id="${modelId}"]`);
        if (!modelCard) return;

        // Add loading state to model card
        modelCard.classList.add('loading');
        
        // Disable all buttons in the model card
        const buttons = modelCard.querySelectorAll('.model-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.6';
        });

        // Create or update spinner
        let spinner = modelCard.querySelector('.model-spinner');
        if (!spinner) {
            spinner = document.createElement('div');
            spinner.className = 'model-spinner';
            spinner.innerHTML = `
                <div class="spinner-container">
                    <div class="spinner"></div>
                    <span class="spinner-text">Initializing...</span>
                </div>
            `;
            modelCard.appendChild(spinner);
        }
        
        this.spinners.set(modelId, spinner);
    }

    /**
     * Hide loading spinner and re-enable model actions
     */
    hideSpinner(modelId) {
        const modelCard = document.querySelector(`[data-model-id="${modelId}"]`);
        if (!modelCard) return;

        // Remove loading state
        modelCard.classList.remove('loading');
        
        // Re-enable buttons
        const buttons = modelCard.querySelectorAll('.model-btn');
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
        });

        // Remove spinner
        const spinner = this.spinners.get(modelId);
        if (spinner) {
            spinner.remove();
            this.spinners.delete(modelId);
        }
    }

    /**
     * Create or update progress bar for model loading
     */
    updateProgress(modelId, stage, percentage, message) {
        const modelCard = document.querySelector(`[data-model-id="${modelId}"]`);
        if (!modelCard) return;

        let progressContainer = modelCard.querySelector('.progress-container');
        if (!progressContainer) {
            progressContainer = document.createElement('div');
            progressContainer.className = 'progress-container';
            progressContainer.innerHTML = `
                <div class="progress-bar-wrapper">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <span class="progress-percentage">0%</span>
                </div>
                <div class="progress-stage"></div>
                <div class="progress-message"></div>
            `;
            modelCard.appendChild(progressContainer);
            this.progressBars.set(modelId, progressContainer);
        }

        // Update progress bar
        const progressFill = progressContainer.querySelector('.progress-fill');
        const progressPercentage = progressContainer.querySelector('.progress-percentage');
        const progressStage = progressContainer.querySelector('.progress-stage');
        const progressMessage = progressContainer.querySelector('.progress-message');

        if (progressFill) progressFill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        if (progressPercentage) progressPercentage.textContent = `${Math.round(percentage)}%`;
        if (progressStage) progressStage.textContent = stage || '';
        if (progressMessage) progressMessage.textContent = message || '';

        // Update spinner text if exists
        const spinner = this.spinners.get(modelId);
        if (spinner) {
            const spinnerText = spinner.querySelector('.spinner-text');
            if (spinnerText) {
                spinnerText.textContent = `${stage}... ${Math.round(percentage)}%`;
            }
        }
    }

    /**
     * Remove progress bar
     */
    hideProgress(modelId) {
        const progressContainer = this.progressBars.get(modelId);
        if (progressContainer) {
            progressContainer.remove();
            this.progressBars.delete(modelId);
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Use the central notification system
        if (typeof notify !== 'undefined') {
            return notify(type, message);
        } else {
            // Fallback to console if notify is not available
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Load model with real-time SSE feedback
     */
    async loadModelWithSSE(modelName) {
        const modelId = this.getModelId(modelName);
        this.loadingModelId = modelId;
        this.showSpinner(modelId);

        if (this.sseEnabled) {
            try {
                // First, initiate the loading process
                const initResponse = await fetch('/api/llm/load', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_name: modelName })
                });

                const initData = await initResponse.json();
                if (!initData.success && !initData.streaming) {
                    throw new Error(initData.message || 'Failed to initiate model loading');
                }

                // Set up SSE connection for progress updates
                const evtSource = new EventSource(`/api/llm/load_stream?model=${encodeURIComponent(modelName)}`);
                this.currentEventSource = evtSource;

                return new Promise((resolve, reject) => {
                    evtSource.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            
                            if (data.error) {
                                this.showToast(data.error, 'error');
                                this.hideSpinner(modelId);
                                this.hideProgress(modelId);
                                evtSource.close();
                                reject(new Error(data.error));
                                return;
                            }

                            if (data.stage && data.pct !== undefined) {
                                this.updateProgress(modelId, data.stage, data.pct, data.message);
                            }

                            if (data.complete) {
                                this.hideSpinner(modelId);
                                this.hideProgress(modelId);
                                this.showToast(data.message || `Model ${modelName} loaded successfully`, 'success');
                                evtSource.close();
                                resolve(data);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    };

                    evtSource.onerror = (error) => {
                        console.error('SSE error:', error);
                        this.hideSpinner(modelId);
                        this.hideProgress(modelId);
                        evtSource.close();
                        
                        // Fallback to regular fetch
                        this.loadModelFallback(modelName).then(resolve).catch((error) => {
                            if (typeof notify !== 'undefined') {
                                notify('error', `Failed to load model: ${error.message}`);
                            }
                            reject(error);
                        });
                    };

                    evtSource.onopen = () => {
                        this.updateProgress(modelId, 'connecting', 0, 'Establishing connection...');
                    };
                });

            } catch (error) {
                console.error('SSE setup failed, falling back to regular fetch:', error);
                return this.loadModelFallback(modelName);
            }
        } else {
            return this.loadModelFallback(modelName);
        }
    }

    /**
     * Fallback method using regular fetch
     */
    async loadModelFallback(modelName) {
        const modelId = this.getModelId(modelName);
        
        try {
            this.updateProgress(modelId, 'loading', 50, 'Loading model...');
            
            const response = await fetch('/api/llm/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });

            const data = await response.json();
            
            this.hideSpinner(modelId);
            this.hideProgress(modelId);

            if (data.success) {
                this.showToast(data.message, 'success');
                return data;
            } else {
                this.showToast(data.message, 'error');
                throw new Error(data.message);
            }
        } catch (error) {
            this.hideSpinner(modelId);
            this.hideProgress(modelId);
            this.showToast(`Error loading model: ${error.message}`, 'error');
            throw error;
        }
    }

    /**
     * Unload model with real-time feedback
     */
    async unloadModel() {
        // For unload, we'll show a simple progress since it's typically faster
        const modelId = 'current'; // Use generic ID for currently loaded model
        this.showSpinner(modelId);

        try {
            this.updateProgress(modelId, 'unloading', 50, 'Unloading model...');

            const response = await fetch('/api/llm/unload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();
            
            this.hideSpinner(modelId);
            this.hideProgress(modelId);

            if (data.success) {
                this.showToast(data.message, 'success');
                return data;
            } else {
                this.showToast(data.message, 'error');
                throw new Error(data.message);
            }
        } catch (error) {
            this.hideSpinner(modelId);
            this.hideProgress(modelId);
            this.showToast(`Error unloading model: ${error.message}`, 'error');
            throw error;
        }
    }

    /**
     * Cancel current loading operation
     */
    cancelLoading() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
        
        if (this.loadingModelId) {
            this.hideSpinner(this.loadingModelId);
            this.hideProgress(this.loadingModelId);
            this.showToast('Model loading cancelled', 'info');
            this.loadingModelId = null;
        }
    }

    /**
     * Get model ID from model name (sanitize for use as CSS selector)
     */
    getModelId(modelName) {
        return modelName.replace(/[^a-zA-Z0-9-_]/g, '_');
    }

    /**
     * Toggle SSE feature
     */
    setSseEnabled(enabled) {
        this.sseEnabled = enabled;
        console.log(`SSE ${enabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
        
        // Clear all progress bars and spinners
        this.progressBars.forEach(bar => bar.remove());
        this.spinners.forEach(spinner => spinner.remove());
        this.progressBars.clear();
        this.spinners.clear();
    }
}

// Global LLM manager instance
const llmManager = new LLMManager();

// Enhanced model loading function
async function loadModel(modelName) {
    try {
        await llmManager.loadModelWithSSE(modelName);
        loadLLMModels(); // Refresh model grid
    } catch (error) {
        console.error('Model loading failed:', error);
    }
}

// Enhanced model unloading function
async function unloadModel() {
    try {
        await llmManager.unloadModel();
        loadLLMModels(); // Refresh model grid
    } catch (error) {
        console.error('Model unloading failed:', error);
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    llmManager.cleanup();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LLMManager, llmManager };
}

