# InstructMesh-PhysiOpt-Integration

A web application for generating 3D models from text descriptions or images using Microsoft's TRELLIS pipeline. The generated models are displayed in an interactive Three.js viewer.

## Features

- **Text-to-3D**: Generate 3D models from natural language descriptions
- **Image-to-3D**: Convert 2D images into 3D models
- **Interactive Viewer**: View and manipulate generated 3D models with Three.js
- **FastAPI Backend**: RESTful API for 3D generation requests
- **Modern UI**: Clean, responsive web interface

## Architecture

```
InstructMesh-PhysiOpt-Integration/
├── backend/              # FastAPI backend server
│   ├── app.py           # Main API application
│   ├── generate.py      # TRELLIS integration module
│   ├── requirements.txt # Python dependencies
│   └── start_backend.sh # Backend startup script
├── frontend/            # Web interface
│   ├── index.html       # Main HTML page
│   ├── js/              # JavaScript modules
│   │   ├── main.js      # Application logic & Three.js renderer
│   │   └── config.js    # Configuration
│   ├── css/             # Stylesheets
│   │   └── main.css     # Main styles
│   └── start_frontend.sh # Frontend startup script
├── results/             # Generated models storage
│   └── models/          # Individual generation folders
└── README.md            # This file
```

## Prerequisites

1. **Conda** or **Miniconda** installed
2. **TRELLIS Pipeline**: Must have TRELLIS installed at `/home/farazfaruqi/trellis-physics`
3. **TRELLIS Conda Environment**: Must have the `trellis` conda environment set up
4. **CUDA-capable GPU** (recommended for faster generation)

## Quick Start

### 1. Activate TRELLIS Environment

This project uses the existing `trellis` conda environment which already has all dependencies:

```bash
conda activate trellis
```

### 2. Install Additional Web Framework Dependencies (if needed)

The trellis environment should already have FastAPI and uvicorn. If not, install:

```bash
conda activate trellis
pip install fastapi uvicorn[standard] python-multipart pydantic
```

### 3. Start the Backend Server

```bash
conda activate trellis  # If not already activated
cd /home/farazfaruqi/InstructMesh-PhysiOpt-Integration/backend
./start_backend.sh
```

The startup script will automatically activate the trellis environment.

The backend will start on `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`

### 4. Start the Frontend Server

Open a new terminal:

```bash
cd /home/farazfaruqi/InstructMesh-PhysiOpt-Integration/frontend
./start_frontend.sh
```

The frontend will start on `http://localhost:8080`

### 5. Use the Application

1. Open your browser to `http://localhost:8080`
2. Enter a text description OR upload an image
3. Click "Generate" to create a 3D model
4. Wait for generation (this may take several minutes)
5. View and interact with the generated 3D model

## Usage

### Text-to-3D Generation

1. Enter a description in the "Input" textarea (e.g., "a modern chair", "a wooden table")
2. Click "Generate"
3. Wait for the model to be generated
4. The 3D model will appear in the viewer below

### Image-to-3D Generation

1. Click "Browse" under the "Image" section
2. Select an image file (PNG, JPG, etc.)
3. Click "Generate"
4. Wait for the model to be generated
5. The 3D model will appear in the viewer below

### 3D Viewer Controls

- **Rotate**: Left-click and drag
- **Pan**: Right-click and drag (or middle mouse button)
- **Zoom**: Scroll wheel
- **Reset View**: Click "Reset View" button
- **Download**: Click "Download Model" to save the GLB file

## Configuration

### Backend Configuration

Edit `/home/farazfaruqi/InstructMesh-PhysiOpt-Integration/backend/generate.py` to modify:
- TRELLIS pipeline paths
- Default generation parameters
- Output formats

### Frontend Configuration

Edit `/home/farazfaruqi/InstructMesh-PhysiOpt-Integration/frontend/js/config.js` to modify:
- Backend API URL (if running on different port/host)

## API Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "message": "InstructMesh-PhysiOpt-Integration backend is running",
  "version": "1.0.0"
}
```

### `POST /generate_from_text`
Generate 3D model from text description.

**Request:**
```json
{
  "text": "a modern chair",
  "seed": 1
}
```

**Response:**
```json
{
  "success": true,
  "generation_id": "uuid-string",
  "model_url": "/files/uuid-string/model.glb",
  "text_prompt": "a modern chair"
}
```

### `POST /generate_from_image`
Generate 3D model from uploaded image.

**Request:**
- Form data with `image` (file) and `seed` (int, optional)

**Response:**
```json
{
  "success": true,
  "generation_id": "uuid-string",
  "model_url": "/files/uuid-string/model.glb",
  "image_filename": "input.jpg"
}
```

### `GET /files/{folder}/{filename}`
Serve generated model files.

## Technology Stack

- **Backend**: FastAPI, PyTorch, TRELLIS
- **Frontend**: HTML5, JavaScript (ES6), Three.js
- **3D Formats**: GLB, OBJ

## File Structure

- **Generated models** are stored in `results/models/{generation_id}/`
- Each generation creates a unique folder with:
  - `model.glb` - 3D model file (primary output)
  - `model.obj` - Alternative format (fallback)
  - `input.{ext}` - Original input image (if applicable)
  - `prompt.txt` - Text prompt (if applicable)

## Troubleshooting

### Backend won't start
- Check that TRELLIS is installed at `/home/farazfaruqi/trellis-physics`
- Verify Python dependencies are installed
- Check port 8000 is not in use

### Generation fails
- Ensure CUDA is available (check with `nvidia-smi`)
- Verify TRELLIS models are downloaded
- Check backend logs for detailed error messages

### Model doesn't display
- Check browser console for errors
- Verify the model file was generated (check `results/models/`)
- Try downloading the model and viewing it in another tool

### CORS errors
- Ensure backend is running on port 8000
- Check frontend `config.js` has correct backend URL
- Verify CORS middleware is configured in `backend/app.py`

