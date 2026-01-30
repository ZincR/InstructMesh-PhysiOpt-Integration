#!/usr/bin/env python3
"""
InstructMesh-PhysiOpt-Integration - Backend API
FastAPI backend for 3D model generation using Microsoft TRELLIS
"""

import os
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Body, Request
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

# Initialize session logger BEFORE other imports
# Use BACKEND_SESSION_ID from env so one log file per backend run (reload workers append to it)
from logger import init_session_logger, get_logger, get_session_logger

_session_id = os.environ.get("BACKEND_SESSION_ID")
if get_session_logger() is None:
    logger_instance = init_session_logger(log_dir="logs", session_id=_session_id)
else:
    logger_instance = get_session_logger()
logger = get_logger()

# Import our generation and optimization modules
from image import generate_image
from generate import generate_3d_from_image
from optimize import optimize_model
from plot_stresses import plot_hexahedral_mesh_surface_stylized

# Import segmentation module
from segment import (
    POINT_SAM_AVAILABLE,
    load_model_for_segmentation,
    clear_prompts,
    get_pointcloud_data,
    segment_with_click
)

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
        return None


def _download_image(url: str, dest_dir: Path) -> Path:
    """Download image from URL to dest_dir; return path to saved file."""
    req = urllib.request.Request(url, headers={"User-Agent": "InstructMesh-Backend/1.0"})
    with urllib.request.urlopen(req) as resp:
        ct = (resp.headers.get("Content-Type") or "").lower()
        ext = ".jpg" if "jpeg" in ct or "jpg" in ct else ".png"
        path = dest_dir / f"generated_image{ext}"
        with open(path, "wb") as f:
            f.write(resp.read())
    return path

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
            "generate": "/generate (POST)"
        },
        "documentation": "Visit http://localhost:8000/docs for interactive API documentation"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="healthy",
        message="InstructMesh-PhysiOpt-Integration backend is running",
        version="1.0.0"
    )

@app.post("/generate")
async def generate(
    text: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    seed: int = Form(1),
):
    """
    Single generate endpoint: text required, images optional. Generates an image via image.py,
    then runs 3D generation (generate.py) on the resulting image.
    """
    imgs = images or []
    prompt = (text or "").strip()
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="Text (prompt) is required.",
        )

    try:
        base_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        generation_id = base_id
        n = 0
        while (FILES_DIR / generation_id).exists():
            n += 1
            generation_id = f"{base_id}_{n}"
        output_folder = FILES_DIR / generation_id
        output_folder.mkdir(parents=True, exist_ok=True)

        # Save uploaded images and pass local paths to image.py
        # image.py will upload them to Fal CDN if needed (for public URLs)
        image_input_paths: List[str] = []
        for i, uf in enumerate(imgs):
            if not uf.content_type or not uf.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="All uploads must be images.")
            ext = Path(uf.filename or "image").suffix or ".png"
            name = f"input_{i}{ext}"
            path = output_folder / name
            with open(path, "wb") as f:
                f.write(await uf.read())
            try:
                Image.open(path).verify()
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid image: {uf.filename}")
            image_input_paths.append(str(path))

        logger.info("Generating image via image.py (prompt=%s, %d images)", prompt, len(image_input_paths))

        # 1. Generate image with image.py (Fal.ai)
        # image.py will handle uploading local paths to Fal CDN if needed
        generated_image_url = generate_image(prompt, image_input_paths)
        logger.info("✓ Image generated!")

        # 2. Download result and run 3D generation with generate.py
        downloaded_path = _download_image(generated_image_url, output_folder)
        logger.info("Starting 3D generation on %s", downloaded_path)

        results = generate_3d_from_image(
            image_path=str(downloaded_path),
            output_folder=str(output_folder),
            seed=seed,
            num_samples=1,
        )

        if not results.get("success"):
            raise HTTPException(
                status_code=500,
                detail=results.get("error", "3D generation failed."),
            )

        model_path = results.get("glb_path") or results.get("obj_path")
        if not model_path:
            raise HTTPException(status_code=500, detail="No model file was generated.")

        response_data = {
            "success": True,
            "generation_id": generation_id,
            "model_url": get_relative_url(model_path),
            "files": {
                "glb": get_relative_url(results.get("glb_path")),
                "obj": get_relative_url(results.get("obj_path")),
                "ply": get_relative_url(results.get("ply_path")),
                "slat": get_relative_url(results.get("slat_path")),
            },
        }
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Generate failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/optimize/{generation_id}")
async def optimize_3d_model(generation_id: str):
    """Optimize a generated 3D model using physics simulation"""
    
    logger.info(f"Optimization request for generation: {generation_id}")
    
    try:
        # Get the folder path for this generation
        folder_path = FILES_DIR / generation_id
        
        if not folder_path.exists():
            logger.warning(f"Generation folder not found: {generation_id}")
            raise HTTPException(status_code=404, detail=f"Generation folder not found: {generation_id}")
        
        # Check if SLAT file exists (required for optimization)
        slat_file = folder_path / "slat_00.pt"
        if not slat_file.exists():
            logger.warning(f"SLAT file not found for generation: {generation_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"SLAT file not found. Optimization requires a SLAT file (slat_00.pt) in the generation folder."
            )
        
        # Run optimization
        logger.info(f"Starting physics optimization for: {generation_id}")
        results = optimize_model(
            folder_path=str(folder_path),
            save_slat=False
        )
        
        if not results.get("success"):
            error_msg = results.get("error", "Unknown error occurred")
            logger.error(f"Optimization failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Optimization failed: {error_msg}")
        
        # Prepare response
        optimized_glb_path = results.get("optimized_glb_path")
        if not optimized_glb_path or not Path(optimized_glb_path).exists():
            logger.error("Optimized GLB file was not created")
            raise HTTPException(status_code=500, detail="Optimized GLB file was not created")
        
        logger.info(f"Optimization successful for: {generation_id}")
        
        stresses_path = folder_path / "stresses.png"
        stresses_opt_path = folder_path / "stresses_optimized.png"
        
        response_data = {
            "success": True,
            "generation_id": generation_id,
            "optimized_model_url": get_relative_url(optimized_glb_path),
            "message": results.get("message", "Optimization completed successfully")
        }
        if stresses_path.exists():
            response_data["stresses_url"] = get_relative_url(str(stresses_path))
        if stresses_opt_path.exists():
            response_data["stresses_optimized_url"] = get_relative_url(str(stresses_opt_path))
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization exception: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/files/{folder}/{filename}")
async def serve_file(folder: str, filename: str):
    """Serve generated files"""
    file_path = FILES_DIR / folder / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

# ============================================================================
# 3D Segmentation Endpoints
# ============================================================================

class Load3DModelRequest(BaseModel):
    model_id: str

@app.post("/load_3d_model")
async def load_3d_model_endpoint(request: Load3DModelRequest):
    """Load a 3D model and prepare it for Point-SAM segmentation"""
    if not POINT_SAM_AVAILABLE:
        return JSONResponse(
            content={"success": False, "error": "Point-SAM not available"}, 
            status_code=503
        )
    
    try:
        model_id = request.model_id
        model_dir = FILES_DIR / model_id
        if not model_dir.exists():
            return JSONResponse(
                content={"success": False, "error": f"Model {model_id} not found"}, 
                status_code=200
            )
        
        model_data, error = load_model_for_segmentation(model_id, FILES_DIR)
        if error:
            return JSONResponse(
                content={"success": False, "error": error}, 
                status_code=200
            )
        
        return JSONResponse(content={
            "success": True, 
            "model_id": model_id,
            "num_points": int(model_data['pc_xyz'].shape[1]),
            "glb_path": model_data['glb_path']
        })
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.post("/clear_3d_prompts")
async def clear_3d_prompts():
    """Clear accumulated prompts for 3D segmentation"""
    from segment import current_ply_data
    
    if current_ply_data is None:
        return JSONResponse(
            content={"success": False, "error": "No 3D model loaded"}, 
            status_code=400
        )
    
    clear_prompts()
    return JSONResponse(content={"success": True, "message": "Prompts cleared"})

@app.get("/get_pointcloud")
async def get_pointcloud():
    """Get the currently loaded point cloud data for Three.js visualization"""
    data, error = get_pointcloud_data()
    if error:
        return JSONResponse(
            content={"success": False, "error": error}, 
            status_code=400
        )
    
    return JSONResponse(content={"success": True, **data})

@app.post("/segment_3d_model")
async def segment_3d_model_endpoint(click_point: dict = Body(...)):
    """Segment a 3D model using Point-SAM with click point (positive/negative prompt)"""
    if not POINT_SAM_AVAILABLE:
        return JSONResponse(
            content={"success": False, "error": "Point-SAM not available"}, 
            status_code=503
        )
    
    result, error = segment_with_click(click_point)
    if error:
        status_code = 400 if "too small" in error else 500
        return JSONResponse(
            content={"success": False, "error": error}, 
            status_code=status_code
        )
    
    return JSONResponse(content={"success": True, **result})

# ============================================================================
# Startup Message
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import atexit
    
    logger.info("Starting InstructMesh-PhysiOpt-Integration Backend...")
    logger.info("Backend will be available at: http://localhost:8000")
    logger.info("API documentation at: http://localhost:8000/docs")
    logger.info(f"Session log file: {logger_instance.get_log_path()}")
    
    # Register cleanup on exit
    def cleanup_logger():
        logger_instance.cleanup()
    
    atexit.register(cleanup_logger)
    
    try:
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        cleanup_logger()
    except Exception as e:
        logger.error(f"Server error: {e}")
        cleanup_logger()
        raise

