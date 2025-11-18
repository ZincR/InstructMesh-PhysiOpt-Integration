# 3D Model Generator

A web application that generates 3D models using Microsoft Trellis with text descriptions and/or images, and displays them using Three.js.

## Features

- Text input for 3D model descriptions
- Image upload support
- Local integration with Microsoft Trellis
- Real-time 3D model rendering with Three.js
- Interactive 3D viewer with orbit controls

## Project Structure

```
InstructMeshOpt/
├── main.py                 # FastAPI backend server
├── trellis_generator.py    # Trellis integration module (implement your Trellis calls here)
├── static/
│   ├── index.html         # Frontend HTML
│   └── app.js             # Frontend JavaScript with Three.js
├── generated_models/       # Directory for generated 3D models
├── temp_images/           # Temporary storage for uploaded images
└── requirements.txt       # Python dependencies
```

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up Trellis:**
   - Clone the [Microsoft Trellis repository](https://github.com/Microsoft/TRELLIS)
   - Install Trellis dependencies and download model checkpoints
   - Implement the `generate_3d_model()` function in `trellis_generator.py` to call your Trellis pipeline

3. **Run the application:**
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload
```

4. **Open your browser and navigate to:**
```
http://localhost:8000
```

## Usage

1. Enter a text description of the 3D model you want to generate in the "Input" field
2. Optionally, upload an image using the "Image" button
3. Click "Generate" to create the 3D model
4. The generated model will appear in the 3D viewer on the right
5. Use mouse to rotate, zoom, and pan the 3D model

## API Endpoints

- `GET /` - Serves the main HTML page
- `GET /api/health` - Health check endpoint (returns Trellis availability status)
- `POST /api/generate` - Generates a 3D model from text/image input
- `GET /api/model/{filename}` - Serves the generated 3D model file

## Implementing Trellis Integration

Edit `trellis_generator.py` and implement the `generate_3d_model()` function. The function signature is:

```python
def generate_3d_model(
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    # Your Trellis implementation here
    # Should return the path to the generated GLB file
```

Example structure:
- Import your Trellis pipeline modules
- Load the appropriate config (text-to-3D or image-to-3D)
- Call the generation pipeline with the provided inputs
- Save the output to `output_path`
- Return the path to the generated file

## Notes

- Generated models are stored in the `generated_models/` directory
- Temporary uploaded images are stored in `temp_images/` and cleaned up after processing
- CORS is currently set to allow all origins. In production, restrict this to your frontend domain
- The placeholder implementation in `trellis_generator.py` creates dummy files for testing - replace it with actual Trellis calls
