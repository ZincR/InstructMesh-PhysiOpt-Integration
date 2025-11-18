from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional
import tempfile
import asyncio
from pathlib import Path

# Import local Trellis generator
from trellis_generator import generate_3d_model, is_trellis_available

app = FastAPI(title="3D Model Generator")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create directories for storing generated models
GENERATED_MODELS_DIR = Path("generated_models")
GENERATED_MODELS_DIR.mkdir(exist_ok=True)

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health_check():
    """Check if Trellis is available"""
    return JSONResponse({
        "status": "ok",
        "trellis_available": is_trellis_available()
    })

@app.post("/api/generate")
async def generate_3d_model_endpoint(
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """
    Generate a 3D model using local Trellis implementation
    """
    if not description and not image:
        raise HTTPException(status_code=400, detail="Either description or image must be provided")
    
    try:
        # Handle image upload if provided
        image_path = None
        if image:
            # Save uploaded image to temporary file
            image_content = await image.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix, dir="temp_images") as tmp_image:
                tmp_image.write(image_content)
                image_path = tmp_image.name
            
            # Create temp_images directory if it doesn't exist
            os.makedirs("temp_images", exist_ok=True)
        
        # Generate output filename
        output_filename = f"model_{tempfile.gettempprefix()}{os.getpid()}.glb"
        output_path = GENERATED_MODELS_DIR / output_filename
        
        # Run Trellis generation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        model_path = await loop.run_in_executor(
            None,
            generate_3d_model,
            description,
            image_path,
            str(output_path)
        )
        
        # Clean up temporary image file
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception:
                pass  # Ignore cleanup errors
        
        # Verify the model file was created
        if not os.path.exists(model_path):
            raise HTTPException(status_code=500, detail="Model generation failed: output file not found")
        
        # Return the file path
        filename = os.path.basename(model_path)
        return JSONResponse({
            "success": True,
            "model_url": f"/api/model/{filename}",
            "file_path": model_path
        })
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating model: {str(e)}")

@app.get("/api/model/{filename}")
async def get_model(filename: str):
    """
    Serve the generated 3D model file
    """
    # Security: prevent path traversal
    filename = os.path.basename(filename)
    file_path = GENERATED_MODELS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Verify the file is in the generated_models directory
    if not str(file_path.resolve()).startswith(str(GENERATED_MODELS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        file_path,
        media_type="model/gltf-binary",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
