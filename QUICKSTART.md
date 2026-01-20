# Quick Start Guide

### Step 1: Activate TRELLIS Environment

This project uses the existing `trellis` conda environment:

```bash
conda activate trellis
```

### Step 2: Install Additional Dependencies (if needed)

Check if FastAPI and uvicorn are installed:

```bash
conda activate trellis
pip install fastapi uvicorn[standard] python-multipart pydantic
```

### Step 3: Start Backend (Terminal 1)

```bash
cd /home/farazfaruqi/InstructMesh-PhysiOpt-Integration/backend
./start_backend.sh
```

Wait for: "Backend will be available at: http://localhost:8000"

### Step 4: Start Frontend (Terminal 2)

```bash
cd /home/farazfaruqi/InstructMesh-PhysiOpt-Integration/frontend
./start_frontend.sh
```

## Using the Application

1. **Open browser** → `http://localhost:8080`
2. **Enter text** (e.g., "a modern chair") OR **upload an image**
3. **Click "Generate"**
4. **Wait** (generation takes 2-5 minutes)
5. **View** the 3D model in the interactive viewer!

## Viewer Controls

- **Rotate**: Left-click + drag
- **Pan**: Right-click + drag
- **Zoom**: Mouse wheel
- **Reset**: "Reset View" button
- **Download**: "Download Model" button

## Notes

- First generation may take longer (models loading)
- Requires TRELLIS installed at `/home/farazfaruqi/trellis-physics`
- GPU recommended for faster generation
- Generated models saved in `results/models/`

## Troubleshooting

**Backend error?** Check that TRELLIS is installed and CUDA is available.

**Model won't load?** Check browser console (F12) for errors.

**Port busy?** The scripts will automatically find the next available port.

