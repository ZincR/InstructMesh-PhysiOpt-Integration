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
        files: '/files'
    }
};

export default config;

