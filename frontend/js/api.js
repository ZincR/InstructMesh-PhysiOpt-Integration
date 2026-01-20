/**
 * API Module
 * Handles all backend API calls
 */

import config from './config.js';

export class API {
    static async checkBackend() {
        try {
            const response = await fetch(`${config.backendUrl}${config.endpoints.health}`);
            const data = await response.json();
            console.log('[API] Backend connection:', data.status);
            return { success: true, data };
        } catch (error) {
            console.error('[API] Backend connection failed:', error);
            return { success: false, error: error.message };
        }
    }

    static async generateFromText(text, seed = 1) {
        try {
            const response = await fetch(`${config.backendUrl}${config.endpoints.generateFromText}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    seed: seed
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Generation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('[API] Generate from text error:', error);
            throw error;
        }
    }

    static async generateFromImage(imageFile, seed = 1) {
        try {
            const formData = new FormData();
            formData.append('image', imageFile);
            formData.append('seed', seed.toString());

            const response = await fetch(`${config.backendUrl}${config.endpoints.generateFromImage}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Generation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('[API] Generate from image error:', error);
            throw error;
        }
    }

    static async optimizeModel(generationId) {
        try {
            const response = await fetch(`${config.backendUrl}${config.endpoints.optimize}/${generationId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Optimization failed');
            }

            return await response.json();
        } catch (error) {
            console.error('[API] Optimize model error:', error);
            throw error;
        }
    }

    static async load3DModel(modelId) {
        try {
            const response = await fetch(`${config.backendUrl}/load_3d_model`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model_id: modelId
                })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('[API] Load 3D model error:', error);
            throw error;
        }
    }

    static async segment3DModel(clickPoint) {
        try {
            const response = await fetch(`${config.backendUrl}/segment_3d_model`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(clickPoint)
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('[API] Segment 3D model error:', error);
            throw error;
        }
    }

    static async clear3DPrompts() {
        try {
            const response = await fetch(`${config.backendUrl}/clear_3d_prompts`, {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            console.error('[API] Clear 3D prompts error:', error);
            throw error;
        }
    }

    static async getPointcloud() {
        try {
            const response = await fetch(`${config.backendUrl}/get_pointcloud`, {
                method: 'GET'
            });
            return await response.json();
        } catch (error) {
            console.error('[API] Get pointcloud error:', error);
            throw error;
        }
    }
}
