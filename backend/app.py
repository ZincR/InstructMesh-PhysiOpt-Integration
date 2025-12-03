#!/usr/bin/env python3
"""
InstructMesh-PhysiOpt-Integration - Backend API
FastAPI backend for 3D model generation using Microsoft TRELLIS
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import sys

# Add TRELLIS to the path
sys.path.append("/home/farazfaruqi/trellis-physics")

# Set environment variables for TRELLIS
os.environ["SPCONV_ALGO"] = "native"

# Import our generation and optimization modules
from generate import generate_3d_from_image, generate_3d_from_text
from optimize import optimize_model

# Initialize FastAPI app
app = FastAPI(
    title="InstructMesh-PhysiOpt-Integration API",
    description="Backend API for 3D model generation using Microsoft TRELLIS",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Directories setup
BASE_DIR = Path(__file__).parent
FILES_DIR = BASE_DIR.parent / "results" / "models"
FILES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/files", StaticFiles(directory=str(FILES_DIR)), name="files")

# ============================================================================
# Helper Functions
# ============================================================================

def get_relative_url(file_path: Optional[str]) -> Optional[str]:
    """
    Convert an absolute file path to a relative URL for serving files.
    
    Args:
        file_path: Absolute path to the file, or None
        
    Returns:
        Relative URL like '/files/{folder}/{filename}', or None if file_path is None
    """
    if not file_path:
        return None
    
    try:
        # Convert to Path object
        path = Path(file_path)
        
        # Get relative path from FILES_DIR
        try:
            relative_path = path.relative_to(FILES_DIR)
        except ValueError:
            # If path is not relative to FILES_DIR, try to extract folder and filename
            # Assumes path structure: .../results/models/{folder}/{filename}
            parts = path.parts
            if "models" in parts:
                models_idx = parts.index("models")
                if models_idx + 2 < len(parts):
                    folder = parts[models_idx + 1]
                    filename = parts[models_idx + 2]
                    relative_path = Path(folder) / filename
                else:
                    return None
            else:
                return None
        
        # Convert to URL path
        url_path = "/files/" + str(relative_path).replace("\\", "/")
        return url_path
        
    except Exception as e:
        print(f"[WARNING] Error converting path to URL: {file_path}, error: {e}")
        return None

# ============================================================================
# Request/Response Models
# ============================================================================

class TextRequest(BaseModel):
    text: str
    seed: int = 1

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "InstructMesh-PhysiOpt-Integration API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "generate_from_text": "/generate_from_text (POST)",
            "generate_from_image": "/generate_from_image (POST)"
        },
        "documentation": "Visit http://localhost:8000/docs for interactive API documentation"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="InstructMesh-PhysiOpt-Integration backend is running",
        version="1.0.0"
    )

@app.post("/generate_from_text")
async def generate_from_text(request: TextRequest):
    """Generate 3D model from text description"""
    
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text description cannot be empty")
    
    print(f"[GENERATE] Generating 3D model from text: '{text}'")
    
    try:
        # Create unique folder for this generation
        generation_id = str(uuid.uuid4())
        output_folder = FILES_DIR / generation_id
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Generate 3D model
        results = generate_3d_from_text(
            text_prompt=text,
            output_folder=str(output_folder),
            seed=request.seed,
            num_samples=1
        )
        
        if not results.get("success"):
            error_msg = results.get("error", "Unknown error occurred")
            raise HTTPException(status_code=500, detail=f"3D generation failed: {error_msg}")
        
        # Prepare response
        model_path = results.get("glb_path") or results.get("obj_path")
        if not model_path:
            raise HTTPException(status_code=500, detail="No model file was generated")
        
        # Prepare response with all generated files
        response_data = {
            "success": True,
            "generation_id": generation_id,
            "model_url": get_relative_url(results.get("glb_path") or results.get("obj_path")),
            "text_prompt": text,
            "files": {
                "glb": get_relative_url(results.get("glb_path")),
                "obj": get_relative_url(results.get("obj_path")),
                "ply": get_relative_url(results.get("ply_path")),
                "slat": get_relative_url(results.get("slat_path"))
            }
        }
        
        print(f"[GENERATE] Successfully generated model: {response_data['model_url']}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in text generation: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/generate_from_image")
async def generate_from_image(
    image: UploadFile = File(...),
    seed: int = Form(1)
):
    """Generate 3D model from uploaded image"""
    
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    print(f"[GENERATE] Generating 3D model from image: {image.filename}")
    
    try:
        # Create unique folder for this generation
        generation_id = str(uuid.uuid4())
        output_folder = FILES_DIR / generation_id
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded image
        image_path = output_folder / f"input_{image.filename}"
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        # Verify it's a valid image
        try:
            Image.open(image_path).verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Generate 3D model
        results = generate_3d_from_image(
            image_path=str(image_path),
            output_folder=str(output_folder),
            seed=seed,
            num_samples=1
        )
        
        if not results.get("success"):
            error_msg = results.get("error", "Unknown error occurred")
            raise HTTPException(status_code=500, detail=f"3D generation failed: {error_msg}")
        
        # Prepare response
        model_path = results.get("glb_path") or results.get("obj_path")
        if not model_path:
            raise HTTPException(status_code=500, detail="No model file was generated")
        
        # Prepare response with all generated files
        response_data = {
            "success": True,
            "generation_id": generation_id,
            "model_url": get_relative_url(results.get("glb_path") or results.get("obj_path")),
            "image_filename": image.filename,
            "files": {
                "glb": get_relative_url(results.get("glb_path")),
                "obj": get_relative_url(results.get("obj_path")),
                "ply": get_relative_url(results.get("ply_path")),
                "slat": get_relative_url(results.get("slat_path"))
            }
        }
        
        print(f"[GENERATE] Successfully generated model: {response_data['model_url']}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in image generation: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/optimize/{generation_id}")
async def optimize_3d_model(generation_id: str):
    """Optimize a generated 3D model using physics simulation"""
    
    print(f"[OPTIMIZE] Optimizing model for generation_id: {generation_id}")
    
    try:
        # Get the folder path for this generation
        folder_path = FILES_DIR / generation_id
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail=f"Generation folder not found: {generation_id}")
        
        # Check if SLAT file exists (required for optimization)
        slat_file = folder_path / "slat_00.pt"
        if not slat_file.exists():
            raise HTTPException(
                status_code=400, 
                detail=f"SLAT file not found. Optimization requires a SLAT file (slat_00.pt) in the generation folder."
            )
        
        # Run optimization
        results = optimize_model(
            folder_path=str(folder_path),
            save_slat=False
        )
        
        if not results.get("success"):
            error_msg = results.get("error", "Unknown error occurred")
            raise HTTPException(status_code=500, detail=f"Optimization failed: {error_msg}")
        
        # Prepare response
        optimized_glb_path = results.get("optimized_glb_path")
        if not optimized_glb_path or not Path(optimized_glb_path).exists():
            raise HTTPException(status_code=500, detail="Optimized GLB file was not created")
        
        response_data = {
            "success": True,
            "generation_id": generation_id,
            "optimized_model_url": get_relative_url(optimized_glb_path),
            "message": results.get("message", "Optimization completed successfully")
        }
        
        print(f"[OPTIMIZE] Optimization completed successfully: {response_data['optimized_model_url']}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/files/{folder}/{filename}")
async def serve_file(folder: str, filename: str):
    """Serve generated files"""
    file_path = FILES_DIR / folder / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

# ============================================================================
# Startup Message
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("Starting InstructMesh-PhysiOpt-Integration Backend...")
    print("Backend will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

