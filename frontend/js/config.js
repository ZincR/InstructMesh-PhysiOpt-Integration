// Configuration file for InstructMesh-PhysiOpt-Integration

const config = {
    // Backend API URL
    backendUrl: 'http://localhost:8000',
    
    // API endpoints
    endpoints: {
        health: '/health',
        generateFromText: '/generate_from_text',
        generateFromImage: '/generate_from_image',
        optimize: '/optimize',
        files: '/files',
        load3DModel: '/load_3d_model',
        segment3DModel: '/segment_3d_model',
        clear3DPrompts: '/clear_3d_prompts',
        getPointcloud: '/get_pointcloud'
    },
    
    // Helper method to get full API URL
    getApiUrl(endpoint) {
        return `${this.backendUrl}${endpoint}`;
    }
};

export default config;

