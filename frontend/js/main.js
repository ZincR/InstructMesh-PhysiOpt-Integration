// InstructMesh-PhysiOpt-Integration - Main Application Logic
import config from './config.js';

class InstructMeshApp {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.currentModelUrl = null;
        this.currentGenerationId = null;
        
        this.init();
    }

    init() {
        console.log('[APP] Initializing InstructMesh-PhysiOpt-Integration...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize Three.js viewer
        this.initThreeViewer();
        
        // Check backend connection
        this.checkBackend();
        
        console.log('[APP] Application initialized');
    }

    setupEventListeners() {
        // Text input
        const textInput = document.getElementById('text-input');
        textInput.addEventListener('input', () => this.updateGenerateButton());
        
        // Image upload
        const imageUpload = document.getElementById('image-upload');
        imageUpload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('file-name').textContent = file.name;
                this.updateGenerateButton();
            } else {
                document.getElementById('file-name').textContent = 'Choose an image file...';
                this.updateGenerateButton();
            }
        });
        
        // Generate button
        document.getElementById('generate-btn').addEventListener('click', () => {
            this.handleGenerate();
        });
        
        // Reset view button
        document.getElementById('reset-view-btn').addEventListener('click', () => {
            this.resetCamera();
        });
        
        // Optimize button
        document.getElementById('optimize-btn').addEventListener('click', () => {
            this.handleOptimize();
        });
        
        // Download button
        document.getElementById('download-btn').addEventListener('click', () => {
            this.downloadModel();
        });
        
        // Close error button
        document.getElementById('close-error-btn').addEventListener('click', () => {
            this.hideError();
        });
    }

    updateGenerateButton() {
        const textInput = document.getElementById('text-input');
        const imageUpload = document.getElementById('image-upload');
        const generateBtn = document.getElementById('generate-btn');
        
        const hasText = textInput.value.trim().length > 0;
        const hasImage = imageUpload.files.length > 0;
        
        generateBtn.disabled = !(hasText || hasImage);
    }

    async checkBackend() {
        try {
            const response = await fetch(`${config.backendUrl}${config.endpoints.health}`);
            const data = await response.json();
            console.log('[APP] Backend connection:', data.status);
        } catch (error) {
            console.error('[APP] Backend connection failed:', error);
            this.showError('Cannot connect to backend. Make sure the backend server is running on port 8000.');
        }
    }

    initThreeViewer() {
        // Check if THREE.js is loaded
        if (typeof THREE === 'undefined') {
            console.error('[APP] THREE.js is not loaded. Please check the CDN link in index.html');
            return;
        }
        
        const viewerContainer = document.getElementById('three-viewer');
        if (!viewerContainer) {
            console.error('[APP] Viewer container not found!');
            return;
        }
        
        // Get dimensions - use offsetWidth/offsetHeight if clientWidth/Height are 0 (container hidden)
        let width = viewerContainer.clientWidth || viewerContainer.offsetWidth || 800;
        let height = viewerContainer.clientHeight || viewerContainer.offsetHeight || 600;
        
        // If still zero, use defaults
        if (width === 0) width = 800;
        if (height === 0) height = 600;
        
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);
        
        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            width / height,
            0.1,
            1000
        );
        this.camera.position.set(0, 0, 5);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        viewerContainer.appendChild(this.renderer.domElement);
        
        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 5, 5);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);
        
        // Grid helper
        const gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(gridHelper);
        
        // Axis helper
        const axesHelper = new THREE.AxesHelper(2);
        this.scene.add(axesHelper);
        
        // Handle window resize
        window.addEventListener('resize', () => {
            const newWidth = viewerContainer.clientWidth || viewerContainer.offsetWidth || 800;
            const newHeight = viewerContainer.clientHeight || viewerContainer.offsetHeight || 600;
            
            if (newWidth > 0 && newHeight > 0) {
                this.camera.aspect = newWidth / newHeight;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(newWidth, newHeight);
            }
        });
        
        console.log('[APP] THREE.js viewer initialized with dimensions:', width, height);
        
        // Animation loop
        this.animate();
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    async handleGenerate() {
        const textInput = document.getElementById('text-input');
        const imageUpload = document.getElementById('image-upload');
        
        const text = textInput.value.trim();
        const imageFile = imageUpload.files[0];
        
        if (!text && !imageFile) {
            this.showError('Please provide either a text description or an image.');
            return;
        }
        
        // Hide previous results and show loading
        this.hideError();
        this.hideViewer();
        this.showLoading();
        
        try {
            let result;
            
            if (imageFile) {
                // Generate from image
                result = await this.generateFromImage(imageFile);
            } else {
                // Generate from text
                result = await this.generateFromText(text);
            }
            
            if (result.success) {
                // Store generation ID for optimization
                this.currentGenerationId = result.generation_id;
                
                // Load and display the 3D model
                await this.loadModel(result.model_url);
                this.currentModelUrl = result.model_url;
                this.showViewer();
            } else {
                throw new Error(result.error || 'Generation failed');
            }
        } catch (error) {
            console.error('[APP] Generation error:', error);
            this.showError(error.message || 'Failed to generate 3D model. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    async generateFromText(text) {
        const response = await fetch(`${config.backendUrl}${config.endpoints.generateFromText}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                seed: 1
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        return await response.json();
    }

    async generateFromImage(imageFile) {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('seed', '1');
        
        const response = await fetch(`${config.backendUrl}${config.endpoints.generateFromImage}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        return await response.json();
    }

    async loadModel(modelUrl) {
        // Remove previous model
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel = null;
        }
        
        const fullUrl = `${config.backendUrl}${modelUrl}`;
        console.log('[APP] Loading model from:', fullUrl);
        
        // Check file extension
        const extension = modelUrl.split('.').pop().toLowerCase();
        
        if (extension === 'glb' || extension === 'gltf') {
            await this.loadGLB(fullUrl);
        } else if (extension === 'obj') {
            await this.loadOBJ(fullUrl);
        } else {
            throw new Error(`Unsupported file format: ${extension}`);
        }
        
        // Fit model to camera
        this.fitModelToCamera();
    }

    async loadGLB(url) {
        return new Promise((resolve, reject) => {
            const loader = new THREE.GLTFLoader();
            loader.load(
                url,
                (gltf) => {
                    const model = gltf.scene;
                    this.currentModel = model;
                    this.scene.add(model);
                    
                    // Enable shadows
                    model.traverse((child) => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                        }
                    });
                    
                    console.log('[APP] GLB model loaded successfully');
                    resolve();
                },
                undefined,
                (error) => {
                    console.error('[APP] Error loading GLB:', error);
                    reject(new Error('Failed to load GLB model'));
                }
            );
        });
    }

    async loadOBJ(url) {
        return new Promise((resolve, reject) => {
            const loader = new THREE.OBJLoader();
            loader.load(
                url,
                (object) => {
                    this.currentModel = object;
                    this.scene.add(object);
                    
                    // Enable shadows
                    object.traverse((child) => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                            // Add basic material if none exists
                            if (!child.material) {
                                child.material = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                            }
                        }
                    });
                    
                    console.log('[APP] OBJ model loaded successfully');
                    resolve();
                },
                undefined,
                (error) => {
                    console.error('[APP] Error loading OBJ:', error);
                    reject(new Error('Failed to load OBJ model'));
                }
            );
        });
    }

    fitModelToCamera() {
        if (!this.currentModel) return;
        
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // Calculate distance to fit model
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;
        
        // Position camera
        this.camera.position.set(
            center.x + distance * 0.7,
            center.y + distance * 0.7,
            center.z + distance * 0.7
        );
        
        // Look at center
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    resetCamera() {
        this.fitModelToCamera();
    }

    downloadModel() {
        if (!this.currentModelUrl) {
            this.showError('No model available to download.');
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

    async handleOptimize() {
        if (!this.currentGenerationId) {
            this.showError('No model available to optimize. Please generate a model first.');
            return;
        }
        
        console.log(`[OPTIMIZE] Starting optimization for generation: ${this.currentGenerationId}`);
        
        // Show loading
        this.hideError();
        this.showLoading();
        
        // Disable optimize button during optimization
        const optimizeBtn = document.getElementById('optimize-btn');
        const originalText = optimizeBtn.textContent;
        optimizeBtn.disabled = true;
        optimizeBtn.textContent = 'Optimizing...';
        
        try {
            const response = await fetch(`${config.backendUrl}${config.endpoints.optimize}/${this.currentGenerationId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Optimization failed');
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log('[OPTIMIZE] Optimization completed successfully');
                console.log('[OPTIMIZE] Optimized model URL:', result.optimized_model_url);
                
                // Load and display the optimized model
                await this.loadModel(result.optimized_model_url);
                this.currentModelUrl = result.optimized_model_url;
                console.log('[OPTIMIZE] Optimized model loaded and displayed');
                this.hideLoading();
                this.showViewer();
            } else {
                throw new Error(result.error || 'Optimization failed');
            }
        } catch (error) {
            console.error('[OPTIMIZE] Error:', error);
            this.hideLoading();
            this.showError(`Optimization failed: ${error.message}`);
        } finally {
            // Re-enable optimize button
            optimizeBtn.disabled = false;
            optimizeBtn.textContent = originalText;
        }
    }

    showLoading() {
        document.getElementById('loading-section').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-section').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('error-text').textContent = message;
        document.getElementById('error-section').classList.remove('hidden');
    }

    hideError() {
        document.getElementById('error-section').classList.add('hidden');
    }

    showViewer() {
        document.getElementById('viewer-section').classList.remove('hidden');
        
        // Resize renderer after showing (container might have been hidden during init)
        if (this.renderer && this.camera) {
            const viewerContainer = document.getElementById('three-viewer');
            if (viewerContainer) {
                const width = viewerContainer.clientWidth || viewerContainer.offsetWidth || 800;
                const height = viewerContainer.clientHeight || viewerContainer.offsetHeight || 600;
                
                if (width > 0 && height > 0) {
                    this.camera.aspect = width / height;
                    this.camera.updateProjectionMatrix();
                    this.renderer.setSize(width, height);
                }
            }
        }
    }

    hideViewer() {
        document.getElementById('viewer-section').classList.add('hidden');
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

