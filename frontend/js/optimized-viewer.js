/**
 * Optimized Three.js Viewer Module
 * Handles the 3D viewer for physics-optimized models
 */

export class OptimizedViewer {
    constructor(containerId) {
        this.containerId = containerId;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
    }

    init() {
        if (typeof THREE === 'undefined') {
            console.error('[OPTIMIZED-VIEWER] THREE.js is not loaded');
            return;
        }

        const viewerContainer = document.getElementById(this.containerId);
        if (!viewerContainer) {
            console.error(`[OPTIMIZED-VIEWER] Container ${this.containerId} not found!`);
            return;
        }

        // Get dimensions
        let width = viewerContainer.clientWidth || viewerContainer.offsetWidth || 800;
        let height = viewerContainer.clientHeight || viewerContainer.offsetHeight || 600;
        if (width === 0) width = 800;
        if (height === 0) height = 600;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // Camera
        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        this.camera.position.set(0, 0, 5);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        if (THREE.sRGBEncoding !== undefined) {
            this.renderer.outputEncoding = THREE.sRGBEncoding;
        }
        if (THREE.ACESFilmicToneMapping !== undefined) {
            this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        }
        this.renderer.toneMappingExposure = 1.5;
        
        // Ensure canvas fills its container
        this.renderer.domElement.style.width = '100%';
        this.renderer.domElement.style.height = '100%';
        this.renderer.domElement.style.display = 'block';
        
        viewerContainer.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
        directionalLight.position.set(5, 5, 5);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight2.position.set(-5, 3, -5);
        this.scene.add(directionalLight2);

        const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.6);
        directionalLight3.position.set(0, 5, -5);
        this.scene.add(directionalLight3);

        // Grid and axis helpers
        const gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(gridHelper);

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
                
                // Ensure canvas fills container
                this.renderer.domElement.style.width = '100%';
                this.renderer.domElement.style.height = '100%';
            }
        });

        console.log(`[OPTIMIZED-VIEWER] Initialized ${this.containerId}`);
    }

    removeCurrentModel() {
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel = null;
        }
    }

    addModel(model) {
        this.removeCurrentModel();
        this.currentModel = model;
        this.scene.add(model);
        
        // Enable shadows and set up materials
        model.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                
                // Ensure proper texture encoding
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach((mat) => {
                            if (mat.map && THREE.sRGBEncoding !== undefined) {
                                mat.map.encoding = THREE.sRGBEncoding;
                            }
                        });
                    } else {
                        if (child.material.map && THREE.sRGBEncoding !== undefined) {
                            child.material.map.encoding = THREE.sRGBEncoding;
                        }
                    }
                }
            }
        });
    }

    fitModelToCamera() {
        if (!this.currentModel) return;
        
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;
        
        this.camera.position.set(
            center.x + distance * 0.7,
            center.y + distance * 0.7,
            center.z + distance * 0.7
        );
        
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    resetCamera() {
        this.fitModelToCamera();
    }

    render() {
        if (this.controls && this.renderer && this.scene && this.camera) {
            this.controls.update();
            this.renderer.render(this.scene, this.camera);
        }
    }

    resize() {
        const viewerContainer = document.getElementById(this.containerId);
        if (viewerContainer && this.renderer && this.camera) {
            const width = viewerContainer.clientWidth || viewerContainer.offsetWidth || 800;
            const height = viewerContainer.clientHeight || viewerContainer.offsetHeight || 600;
            
            if (width > 0 && height > 0) {
                this.camera.aspect = width / height;
                this.camera.updateProjectionMatrix();
                this.renderer.setSize(width, height);
                
                // Ensure canvas fills container
                this.renderer.domElement.style.width = '100%';
                this.renderer.domElement.style.height = '100%';
            }
        }
    }
}
