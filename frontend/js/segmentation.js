/**
 * Segmentation Module
 * Handles 3D model segmentation using Point-SAM
 */

import { API } from './api.js';

export class Segmentation {
    constructor(viewer, ui) {
        this.viewer = viewer;
        this.ui = ui;
        this.segmentationMode = false;
        this.current3DSegmentationData = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.originalMeshColors = null;
        this.originalTextures = null;
    }

    setupHandlers() {
        const viewerElement = this.viewer.renderer.domElement;
        
        // Left click - positive prompt
        viewerElement.addEventListener('click', (event) => {
            if (this.segmentationMode && this.viewer.getModel()) {
                this.handleModelClick(event, true);
            }
        });
        
        // Right click - negative prompt
        viewerElement.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            if (this.segmentationMode && this.viewer.getModel()) {
                this.handleModelClick(event, false);
            }
        });
    }

    handleModelClick(event, isPositivePrompt) {
        const rect = this.viewer.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.raycaster.setFromCamera(this.mouse, this.viewer.camera);
        const intersects = this.raycaster.intersectObject(this.viewer.getModel(), true);
        
        if (intersects.length > 0) {
            const point = intersects[0].point;
            this.handle3DPointClick(point, isPositivePrompt);
        } else {
            console.log('[Segmentation] Click did not intersect with model');
        }
    }

    setOriginalTextures(textures) {
        this.originalTextures = textures;
    }

    setOriginalMeshColors(colors) {
        this.originalMeshColors = colors;
    }

    async enable() {
        // This will be called with generationId from main app
        console.log('[Segmentation] Enabling segmentation mode');
        this.segmentationMode = true;
        this.current3DSegmentationData = { mode: 'enabled', promptCount: 0 };
        
        this.ui.updateSegmentButton('✅ Click on model to segment', false);
        this.ui.showClearSegmentationButton();
        this.ui.showSegmentationInfo();
        this.ui.updateSegmentationInstructions('Segmentation enabled! Left-click: positive, Right-click: negative');
    }

    async clear() {
        // Clear prompts in backend
        try {
            await API.clear3DPrompts();
        } catch (error) {
            console.warn('[Segmentation] Could not clear backend prompts:', error);
        }
        
        // Reset segmentation state
        this.segmentationMode = false;
        this.current3DSegmentationData = null;
        
        // Reset model colors and textures
        this.resetModelVisualization();
        
        this.ui.updateSegmentButton('🧊 Segment 3D Model');
        this.ui.updateSegmentationInstructions('Click "Segment 3D Model" to enable interactive segmentation');
        console.log('[Segmentation] Segmentation cleared');
    }

    async handle3DPointClick(point, isPositivePrompt) {
        if (!this.current3DSegmentationData || this.current3DSegmentationData.mode !== 'enabled') {
            return;
        }
        
        const promptType = isPositivePrompt ? 'positive' : 'negative';
        console.log(`[Segmentation] ${promptType} prompt clicked:`, point);
        
        this.ui.updateSegmentationInstructions(`Adding ${promptType} prompt and segmenting...`);
        this.ui.updateSegmentButton('Segmenting...', true);
        
        try {
            const response = await API.segment3DModel({
                x: point.x,
                y: point.y,
                z: point.z,
                prompt_label: isPositivePrompt ? 1 : 0
            });
            
            if (response.success) {
                const previousPromptCount = this.current3DSegmentationData.promptCount || 0;
                this.current3DSegmentationData = {
                    segment: response.segment,
                    mask: response.mask,
                    mode: 'enabled',
                    promptCount: previousPromptCount + 1
                };
                
                // Apply segmentation visualization
                this.applySegmentationToMesh(response.mask, response.segment);
                
                this.ui.updateSegmentButton('Segmented! Click again to refine', false);
                const promptCount = this.current3DSegmentationData.promptCount;
                this.ui.updateSegmentationInstructions(
                    `Segment: ${response.segment.num_points} points (${promptCount} prompts). Blue areas are segmented. Continue clicking to refine.`
                );
                
                console.log('[Segmentation] Segmentation successful:', response.segment);
            } else {
                throw new Error(response.error || 'Segmentation failed');
            }
        } catch (error) {
            console.error('[Segmentation] Error:', error);
            this.ui.updateSegmentButton('Segment 3D Model', false);
            throw error;
        }
    }

    applySegmentationToMesh(mask, segment) {
        const model = this.viewer.getModel();
        if (!model || !mask) return;
        
        // Find all meshes
        const meshes = [];
        model.traverse((child) => {
            if (child.isMesh && child.geometry) {
                meshes.push(child);
            }
        });
        
        if (meshes.length === 0) return;
        
        const mesh = meshes[0];
        const geometry = mesh.geometry;
        const positions = geometry.attributes.position;
        
        if (!positions) return;
        
        // Get or create color attribute
        let colors = geometry.attributes.color;
        if (!colors) {
            const defaultColors = new Float32Array(positions.count * 3);
            for (let i = 0; i < positions.count; i++) {
                defaultColors[i * 3] = 0.7;
                defaultColors[i * 3 + 1] = 0.7;
                defaultColors[i * 3 + 2] = 0.7;
            }
            colors = new THREE.BufferAttribute(defaultColors, 3);
            geometry.setAttribute('color', colors);
            if (!this.originalMeshColors) {
                this.originalMeshColors = defaultColors.slice();
            }
        }
        
        const colorArray = colors.array;
        const defaultColor = [1.0, 1.0, 1.0];
        const segmentColor = [0.2, 0.4, 1.0]; // Blue
        
        // Calculate mesh bounding box
        const box = new THREE.Box3().setFromBufferAttribute(positions);
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const threshold = maxDim * 0.05;
        const thresholdSq = threshold * threshold;
        
        // Apply segmentation colors
        if (segment && segment.point_indices && segment.points) {
            const vertexPositions = positions.array;
            const segmentPoints = segment.points.map(p => ({
                x: p[0] || p.x || 0,
                y: p[1] || p.y || 0,
                z: p[2] || p.z || 0
            }));
            
            for (let vIdx = 0; vIdx < positions.count; vIdx++) {
                const vx = vertexPositions[vIdx * 3];
                const vy = vertexPositions[vIdx * 3 + 1];
                const vz = vertexPositions[vIdx * 3 + 2];
                
                let isSegmented = false;
                
                for (let pIdx = 0; pIdx < segmentPoints.length; pIdx++) {
                    const p = segmentPoints[pIdx];
                    const dx = vx - p.x;
                    const dy = vy - p.y;
                    const dz = vz - p.z;
                    const distSq = dx * dx + dy * dy + dz * dz;
                    
                    if (distSq < thresholdSq) {
                        isSegmented = true;
                        break;
                    }
                }
                
                if (isSegmented) {
                    colorArray[vIdx * 3] = segmentColor[0];
                    colorArray[vIdx * 3 + 1] = segmentColor[1];
                    colorArray[vIdx * 3 + 2] = segmentColor[2];
                } else {
                    if (this.originalMeshColors && vIdx * 3 + 2 < this.originalMeshColors.length) {
                        colorArray[vIdx * 3] = this.originalMeshColors[vIdx * 3];
                        colorArray[vIdx * 3 + 1] = this.originalMeshColors[vIdx * 3 + 1];
                        colorArray[vIdx * 3 + 2] = this.originalMeshColors[vIdx * 3 + 2];
                    } else {
                        colorArray[vIdx * 3] = defaultColor[0];
                        colorArray[vIdx * 3 + 1] = defaultColor[1];
                        colorArray[vIdx * 3 + 2] = defaultColor[2];
                    }
                }
            }
        }
        
        colors.needsUpdate = true;
        geometry.attributes.color.needsUpdate = true;
        
        // Enable vertex colors in materials
        meshes.forEach(m => {
            if (m.material) {
                if (Array.isArray(m.material)) {
                    m.material.forEach(mat => {
                        mat.vertexColors = true;
                        mat.map = null;
                        mat.color = new THREE.Color(1, 1, 1);
                        mat.needsUpdate = true;
                    });
                } else {
                    m.material.vertexColors = true;
                    m.material.map = null;
                    m.material.color = new THREE.Color(1, 1, 1);
                    m.material.needsUpdate = true;
                }
            }
        });
    }

    resetModelVisualization() {
        const model = this.viewer.getModel();
        if (!model) return;
        
        model.traverse((child) => {
            if (child.isMesh && child.geometry) {
                // Restore original colors
                const colors = child.geometry.attributes.color;
                if (colors && this.originalMeshColors) {
                    const colorArray = colors.array;
                    for (let i = 0; i < Math.min(this.originalMeshColors.length, colorArray.length); i++) {
                        colorArray[i] = this.originalMeshColors[i];
                    }
                    colors.needsUpdate = true;
                }
                
                // Restore original textures
                if (this.originalTextures && child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(mat => {
                            const textureData = this.originalTextures.find(t => t.material === mat);
                            if (textureData) {
                                mat.map = textureData.map;
                                mat.vertexColors = false;
                                if (THREE.sRGBEncoding !== undefined && mat.map) {
                                    mat.map.encoding = THREE.sRGBEncoding;
                                }
                                mat.needsUpdate = true;
                            }
                        });
                    } else {
                        const textureData = this.originalTextures.find(t => t.material === child.material);
                        if (textureData) {
                            child.material.map = textureData.map;
                            child.material.vertexColors = false;
                            if (THREE.sRGBEncoding !== undefined && child.material.map) {
                                child.material.map.encoding = THREE.sRGBEncoding;
                            }
                            child.material.needsUpdate = true;
                        }
                    }
                }
            }
        });
    }
}
