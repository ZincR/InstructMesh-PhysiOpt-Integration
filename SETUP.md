# Setup Instructions

## Using Existing TRELLIS Environment

This project uses the existing `trellis` conda environment, which already contains all TRELLIS dependencies.

### Step 1: Activate TRELLIS Environment

```bash
conda activate trellis
```

### Step 2: Install Web Framework Dependencies

The trellis environment may need a few additional packages for the FastAPI web server:

```bash
conda activate trellis
pip install fastapi uvicorn[standard] python-multipart pydantic
```

These should already be installed, but run this to ensure they're available.

### Step 3: Verify Setup

Check that TRELLIS and all dependencies are available:

```bash
conda activate trellis
python3 -c "
import sys
sys.path.insert(0, '/home/farazfaruqi/trellis-physics')
from trellis.pipelines import TrellisTextTo3DPipeline, TrellisImageTo3DPipeline
from trellis.physics.optimizer_factory import OptimizerFactory
print('✓ All dependencies available!')
"
```

If you see "✓ All dependencies available!", you're ready to go!

## Starting the Application

See [QUICKSTART.md](QUICKSTART.md) for instructions on starting the backend and frontend servers.

## Notes

- The `trellis` environment is already configured with all TRELLIS dependencies
- No need to create a separate environment
- TRELLIS should be installed at `/home/farazfaruqi/trellis-physics`

