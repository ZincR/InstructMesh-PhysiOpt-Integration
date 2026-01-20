/**
 * Main Application - InstructMesh-PhysiOpt-Integration
 * Orchestrates all modules and handles event coordination
 */

import config from './config.js';
import { Viewer } from './viewer.js';
import { OptimizedViewer } from './optimized-viewer.js';
import { ModelLoader } from './model-loader.js';
import { API } from './api.js';
import { UI } from './ui.js';
import { Segmentation } from './segmentation.js';

class InstructMeshApp {
    constructor() {
        // State
        this.currentModelUrl = null;
        this.optimizedModelUrl = null;
        this.currentGenerationId = null;
        
        // Modules
        this.viewer = new Viewer('three-viewer');
        this.optimizedViewer = new OptimizedViewer('three-viewer-optimized');
        this.segmentation = new Segmentation(this.viewer, UI);
        
        this.init();
    }

    init() {
        console.log('[APP] Initializing InstructMesh-PhysiOpt-Integration...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize Three.js viewers
        this.viewer.init();
        this.optimizedViewer.init();
        
        // Setup segmentation handlers
        this.segmentation.setupHandlers();
        
        // Check backend connection
        this.checkBackend();
        
        // Start animation loop
        this.animate();
        
        console.log('[APP] Application initialized');
    }

    setupEventListeners() {
        // Text input
        const textInput = document.getElementById('text-input');
        textInput.addEventListener('input', () => UI.updateGenerateButton());
        
        // Image upload
        const imageUpload = document.getElementById('image-upload');
        imageUpload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            UI.updateFileName(file ? file.name : null);
            UI.updateGenerateButton();
        });
        
        // Generate button
        document.getElementById('generate-btn').addEventListener('click', () => {
            this.handleGenerate();
        });
        
        // Reset view buttons
        document.getElementById('reset-view-btn').addEventListener('click', () => {
            this.viewer.resetCamera();
        });
        
        document.getElementById('reset-view-optimized-btn').addEventListener('click', () => {
            this.optimizedViewer.resetCamera();
        });
        
        // Optimize button
        document.getElementById('optimize-btn').addEventListener('click', () => {
            this.handleOptimize();
        });
        
        // Download buttons
        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadModel();
        });
        
        document.getElementById('download-optimized-btn').addEventListener('click', () => {
            this.downloadOptimizedModel();
        });
        
        // Segmentation buttons
        const segmentBtn = document.getElementById('segment-3d-btn');
        if (segmentBtn) {
            segmentBtn.addEventListener('click', async () => {
                await this.enableSegmentation();
            });
        }
        
        const clearSegBtn = document.getElementById('clear-segmentation-btn');
        if (clearSegBtn) {
            clearSegBtn.addEventListener('click', async () => {
                await this.clearSegmentation();
            });
        }
        
        // Close error button
        document.getElementById('close-error-btn').addEventListener('click', () => {
            UI.hideError();
        });
    }

    async checkBackend() {
        const result = await API.checkBackend();
        if (!result.success) {
            UI.showError('Cannot connect to backend. Make sure the backend server is running on port 8000.');
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.viewer.render();
        this.optimizedViewer.render();
    }

    async handleGenerate() {
        const textInput = document.getElementById('text-input');
        const imageUpload = document.getElementById('image-upload');
        
        const text = textInput.value.trim();
        const imageFile = imageUpload.files[0];
        
        if (!text && !imageFile) {
            UI.showError('Please provide either a text description or an image.');
            return;
        }
        
        // Hide previous results and show loading
        UI.hideError();
        UI.hideViewer();
        UI.hideOptimizedViewer();
        UI.showLoading();
        
        try {
            let result;
            
            if (imageFile) {
                result = await API.generateFromImage(imageFile);
            } else {
                result = await API.generateFromText(text);
            }
            
            if (result.success) {
                // Store generation ID for optimization
                this.currentGenerationId = result.generation_id;
                
                // Load and display the 3D model
                await this.loadModel(result.model_url);
                this.currentModelUrl = result.model_url;
                
                // Reset optimized viewer state
                this.optimizedViewer.removeCurrentModel();
                this.optimizedModelUrl = null;
                
                UI.showViewer();
                UI.showSegmentationButton();
                UI.showSegmentationInfo();
            } else {
                throw new Error(result.error || 'Generation failed');
            }
        } catch (error) {
            console.error('[APP] Generation error:', error);
            UI.showError(error.message || 'Failed to generate 3D model. Please try again.');
        } finally {
            UI.hideLoading();
        }
    }

    async loadModel(modelUrl) {
        try {
            const model = await ModelLoader.loadModel(modelUrl, config.backendUrl);
            
            // Load model into viewer and store textures/colors for segmentation
            this.viewer.addModel(model);
            this.viewer.fitModelToCamera();
            
            // Pass original textures and colors to segmentation
            this.segmentation.setOriginalTextures(this.viewer.originalTextures);
            this.segmentation.setOriginalMeshColors(this.viewer.originalMeshColors);
            
            // Resize viewer
            this.viewer.resize();
        } catch (error) {
            console.error('[APP] Error loading model:', error);
            throw error;
        }
    }

    async handleOptimize() {
        if (!this.currentGenerationId) {
            UI.showError('No model available to optimize. Please generate a model first.');
            return;
        }
        
        console.log(`[OPTIMIZE] Starting optimization for generation: ${this.currentGenerationId}`);
        
        // Show loading
        UI.hideError();
        UI.showLoading();
        
        // Disable optimize button during optimization
        const optimizeBtn = document.getElementById('optimize-btn');
        const originalText = optimizeBtn.textContent;
        optimizeBtn.disabled = true;
        optimizeBtn.textContent = 'Optimizing...';
        
        try {
            const result = await API.optimizeModel(this.currentGenerationId);
            
            if (result.success) {
                console.log('[OPTIMIZE] Optimization completed successfully');
                
                // Load optimized model into optimized viewer
                await this.loadOptimizedModel(result.optimized_model_url);
                this.optimizedModelUrl = result.optimized_model_url;
                
                // Show optimized viewer section
                UI.showOptimizedViewer();
                
                console.log('[OPTIMIZE] Optimized model loaded and displayed in separate viewer');
            } else {
                throw new Error(result.error || 'Optimization failed');
            }
        } catch (error) {
            console.error('[OPTIMIZE] Error:', error);
            UI.showError(`Optimization failed: ${error.message}`);
        } finally {
            UI.hideLoading();
            // Re-enable optimize button
            optimizeBtn.disabled = false;
            optimizeBtn.textContent = originalText;
        }
    }

    async loadOptimizedModel(modelUrl) {
        try {
            const model = await ModelLoader.loadModel(modelUrl, config.backendUrl);
            this.optimizedViewer.addModel(model);
            this.optimizedViewer.fitModelToCamera();
            this.optimizedViewer.resize();
        } catch (error) {
            console.error('[APP] Error loading optimized model:', error);
            throw error;
        }
    }

    downloadModel() {
        if (!this.currentModelUrl) {
            UI.showError('No model available to download.');
            return;
        }
        
        const fullUrl = `${config.backendUrl}${this.currentModelUrl}`;
        const link = document.createElement('a');
        link.href = fullUrl;
        link.download = this.currentModelUrl.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    downloadOptimizedModel() {
        if (!this.optimizedModelUrl) {
            UI.showError('No optimized model available to download.');
            return;
        }
        
        const fullUrl = `${config.backendUrl}${this.optimizedModelUrl}`;
        const link = document.createElement('a');
        link.href = fullUrl;
        link.download = this.optimizedModelUrl.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async enableSegmentation() {
        if (!this.currentGenerationId) {
            UI.showError('Please generate a model first before segmenting.');
            return;
        }
        
        try {
            const response = await API.load3DModel(this.currentGenerationId);
            
            if (!response.success) {
                throw new Error(response.error || 'Failed to load model for segmentation');
            }
            
            console.log('[Segmentation] Model loaded for segmentation:', response);
            await this.segmentation.enable();
        } catch (error) {
            console.error('[Segmentation] Error enabling segmentation:', error);
            UI.showError(`Failed to enable segmentation: ${error.message}`);
        }
    }

    async clearSegmentation() {
        try {
            await this.segmentation.clear();
        } catch (error) {
            console.error('[Segmentation] Error clearing segmentation:', error);
            UI.showError(`Failed to clear segmentation: ${error.message}`);
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new InstructMeshApp();
    });
} else {
    new InstructMeshApp();
}
