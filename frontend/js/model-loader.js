/**
 * Model Loader Module
 * Handles loading of GLB and OBJ files into Three.js scenes
 */

export class ModelLoader {
    /**
     * Convert Z-up to Y-up coordinate system
     * Models are exported with y_up=False (Z-axis up)
     * Three.js uses Y-axis up by default
     * 
     * If Z is up in the model and we want Y up in Three.js:
     * - Z (up) should become Y (up)
     * - Y should become -Z
     * - X should stay X
     * 
     * Rotate -90 degrees around X-axis converts:
     * - Z -> Y (up)
     * - Y -> -Z
     * - X -> X
     */
    static convertZUpToYUp(model) {
        // Rotate -90 degrees around X-axis
        // This converts: Z (up) -> Y (up), Y -> -Z, X -> X
        model.rotation.x = -Math.PI / 2;
        
        // Also ensure the model updates its matrix
        model.updateMatrixWorld(true);
        
        return model;
    }

    static async loadGLB(url) {
        return new Promise((resolve, reject) => {
            const loader = new THREE.GLTFLoader();
            loader.load(
                url,
                (gltf) => {
                    const model = gltf.scene;
                    
                    // Convert from Z-up to Y-up (models are exported with y_up=False)
                    this.convertZUpToYUp(model);
                    
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
                    
                    console.log('[MODEL-LOADER] GLB model loaded successfully (converted from Z-up to Y-up)');
                    resolve(model);
                },
                undefined,
                (error) => {
                    console.error('[MODEL-LOADER] Error loading GLB:', error);
                    reject(new Error('Failed to load GLB model'));
                }
            );
        });
    }

    static async loadOBJ(url) {
        return new Promise((resolve, reject) => {
            const loader = new THREE.OBJLoader();
            loader.load(
                url,
                (object) => {
                    // Convert from Z-up to Y-up (OBJ files are also exported with Z-up)
                    this.convertZUpToYUp(object);
                    
                    // Enable shadows and set up materials
                    object.traverse((child) => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                            
                            // Add basic material if none exists
                            if (!child.material) {
                                child.material = new THREE.MeshStandardMaterial({ 
                                    color: 0xcccccc
                                });
                            } else {
                                // Ensure material has a color if no texture
                                if (!child.material.map && !child.material.color) {
                                    child.material.color = new THREE.Color(0xcccccc);
                                }
                            }
                        }
                    });
                    
                    console.log('[MODEL-LOADER] OBJ model loaded successfully (converted from Z-up to Y-up)');
                    resolve(object);
                },
                undefined,
                (error) => {
                    console.error('[MODEL-LOADER] Error loading OBJ:', error);
                    reject(new Error('Failed to load OBJ model'));
                }
            );
        });
    }

    static async loadModel(modelUrl, baseUrl) {
        const fullUrl = baseUrl ? `${baseUrl}${modelUrl}` : modelUrl;
        const extension = modelUrl.split('.').pop().toLowerCase();
        
        if (extension === 'glb' || extension === 'gltf') {
            return await this.loadGLB(fullUrl);
        } else if (extension === 'obj') {
            return await this.loadOBJ(fullUrl);
        } else {
            throw new Error(`Unsupported file format: ${extension}`);
        }
    }
}
