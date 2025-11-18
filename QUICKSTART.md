# Quick Start Guide

## Step 1: Activate the Virtual Environment

Every time you open a new terminal, activate the virtual environment:

**On macOS/Linux:**

```bash
source venv/bin/activate
```

**On Windows:**

```bash
venv\Scripts\activate
```

You'll know it's activated when you see `(venv)` at the beginning of your terminal prompt.

## Step 2: Set Up Trellis Integration

The project uses a local Trellis implementation. You need to:

1. **Clone the Trellis repository** (if you haven't already):

```bash
# Navigate to a suitable location
cd /path/to/your/projects
git clone https://github.com/Microsoft/TRELLIS.git
```

2. **Implement the Trellis integration** in `trellis_generator.py`:
   - Open `trellis_generator.py` in your editor
   - Replace the placeholder `generate_3d_model()` function with your actual Trellis pipeline calls
   - Import the necessary Trellis modules
   - Configure the model paths and checkpoints

See the `README.md` for more details on implementing the integration.

## Step 3: Run the Server

With the virtual environment activated, run:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

## Step 4: Open in Browser

Navigate to:

```
http://localhost:8000
```

## Using the Application

1. **Enter a description** in the "Input" text field (e.g., "a red sports car")
2. **Optionally upload an image** using the "Image" button
3. **Click "Generate"** to create the 3D model
4. **View the result** in the 3D viewer on the right
5. **Interact with the model** using your mouse:
   - Left click + drag: Rotate
   - Right click + drag: Pan
   - Scroll: Zoom

## Health Check

Check if Trellis is properly integrated:

```
http://localhost:8000/api/health
```

This will return `{"status": "ok", "trellis_available": true/false}`

## Stopping the Server

Press `Ctrl+C` in the terminal to stop the server.

## Deactivating the Virtual Environment

When you're done, deactivate the virtual environment:

```bash
deactivate
```

## Troubleshooting

- **"Trellis not available"**: Make sure you've implemented the `generate_3d_model()` function in `trellis_generator.py`
- **Import errors**: Ensure all Trellis dependencies are installed in your environment
- **Model generation fails**: Check that model checkpoints are downloaded and paths are correctly configured
