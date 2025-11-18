import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Initialize Three.js scene
let scene, camera, renderer, controls, currentModel = null;

function initThreeJS() {
    const canvas = document.getElementById('canvas');
    const container = canvas.parentElement;
    
    // Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);
    
    // Camera setup
    camera = new THREE.PerspectiveCamera(
        75,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 0, 5);
    
    // Renderer setup
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    
    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight1.position.set(5, 5, 5);
    scene.add(directionalLight1);
    
    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-5, -5, -5);
    scene.add(directionalLight2);
    
    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    
    // Handle window resize
    window.addEventListener('resize', onWindowResize);
    
    // Animation loop
    animate();
}

function onWindowResize() {
    const container = renderer.domElement.parentElement;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

function loadModel(url) {
    const loader = new GLTFLoader();
    
    // Remove existing model
    if (currentModel) {
        scene.remove(currentModel);
        currentModel = null;
    }
    
    loader.load(
        url,
        (gltf) => {
            currentModel = gltf.scene;
            scene.add(currentModel);
            
            // Center and scale the model
            const box = new THREE.Box3().setFromObject(currentModel);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            
            // Center the model
            currentModel.position.sub(center);
            
            // Scale to fit
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = 3 / maxDim;
            currentModel.scale.multiplyScalar(scale);
            
            // Adjust camera
            camera.position.set(0, 0, 5);
            controls.target.set(0, 0, 0);
            controls.update();
            
            document.getElementById('emptyState').classList.add('hidden');
        },
        (progress) => {
            console.log('Loading progress:', (progress.loaded / progress.total * 100) + '%');
        },
        (error) => {
            console.error('Error loading model:', error);
            showError('Failed to load 3D model: ' + error.message);
            document.getElementById('loading').classList.remove('active');
        }
    );
}

// Handle image file selection
document.getElementById('imageInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('fileName').textContent = `Selected: ${file.name}`;
    } else {
        document.getElementById('fileName').textContent = '';
    }
});

async function generateModel() {
    const description = document.getElementById('description').value.trim();
    const imageFile = document.getElementById('imageInput').files[0];
    
    if (!description && !imageFile) {
        showError('Please provide either a description or an image');
        return;
    }
    
    // Show loading state
    document.getElementById('loading').classList.add('active');
    document.getElementById('errorMessage').classList.remove('active');
    document.getElementById('generateButton').disabled = true;
    document.getElementById('emptyState').classList.add('hidden');
    
    try {
        const formData = new FormData();
        
        if (description) {
            formData.append('description', description);
        }
        
        if (imageFile) {
            formData.append('image', imageFile);
        }
        
        const response = await fetch('/api/generate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate model');
        }
        
        const result = await response.json();
        
        if (result.success && result.model_url) {
            // Load the 3D model
            loadModel(result.model_url);
        } else {
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to generate 3D model');
    } finally {
        document.getElementById('loading').classList.remove('active');
        document.getElementById('generateButton').disabled = false;
    }
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.add('active');
}

// Make generateModel available globally for the onclick handler
window.generateModel = generateModel;

// Initialize Three.js when page loads
initThreeJS();

