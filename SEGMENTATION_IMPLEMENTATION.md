# 3D Segmentation Implementation Documentation

## Overview

The 3D segmentation functionality enables interactive segmentation of 3D models using positive and negative click inputs. The system uses Point-SAM (Point Cloud Segment Anything Model) to perform real-time segmentation based on user clicks on the 3D model displayed in the Three.js viewer.

## Architecture

The segmentation system consists of two main components:

1. **Backend (`backend/segment.py`)**: Handles Point-SAM model initialization, point cloud processing, and segmentation inference
2. **Frontend (`frontend/js/main.js`)**: Manages user interactions, click handling, and visualization of segmentation results

## Backend Implementation

### Point-SAM Initialization

The Point-SAM model is initialized on module import in `segment.py`:

- **Model Path**: `/home/farazfaruqi/Point-SAM/checkpoints/model.safetensors`
- **Config Path**: `/home/farazfaruqi/Point-SAM/configs` (relative to backend directory)
- **Dependencies**: 
  - CUDA (required for GPU acceleration)
  - NVIDIA Apex (for FusedLayerNorm optimization)
  - torkit3d (for sparse tensor operations)
  - Hydra (for configuration management)

The initialization process:
1. Checks CUDA availability
2. Clears any existing Hydra instances
3. Loads configuration from Hydra
4. Instantiates the model
5. Applies FusedLayerNorm replacement for optimization
6. Loads model weights from safetensors
7. Sets model to evaluation mode and moves to CUDA

If initialization fails, `POINT_SAM_AVAILABLE` is set to `False` and segmentation endpoints return appropriate error messages.

### Model Loading (`load_model_for_segmentation`)

When a user requests segmentation, the backend:

1. **Finds the GLB file**: Searches for `model.glb`, `sample_00.glb`, or any `.glb` file in the model directory
2. **Loads and processes the GLB**: Uses `load_glb_for_point_sam()` to:
   - Load the mesh using trimesh
   - Handle Scene objects (extract geometry from scenes)
   - Sample points from the mesh surface (default: 10,000 points)
   - Extract colors from face or vertex colors if available
   - Normalize point coordinates for Point-SAM
3. **Normalization**: 
   - Centers points by subtracting mean
   - Scales to unit sphere by dividing by maximum distance from center
   - Stores shift and scale for denormalization later
4. **Stores model data**: Creates `current_ply_data` dictionary containing:
   - Normalized point coordinates (`pc_xyz`)
   - Point colors (`pc_rgb`)
   - Normalization parameters (`shift`, `scale`)
   - Model metadata (`model_id`, `glb_path`)
   - Prompt tracking (`prompts`, `labels`, `prompt_mask`)

### Segmentation Process (`segment_with_click`)

When a user clicks on the model:

1. **Click Point Processing**:
   - Receives 3D coordinates (x, y, z) from frontend
   - Receives prompt label (1 = positive, 0 = negative)
   - Converts click point to normalized coordinates using stored shift/scale
   - Adds prompt to accumulated prompts list

2. **Point-SAM Inference**:
   - Converts accumulated prompts to PyTorch tensors
   - Calls `point_sam_model.predict_masks()` with:
     - Point cloud (xyz and rgb)
     - Prompt points (normalized coordinates)
     - Prompt labels (positive/negative)
     - Previous mask (for iterative refinement)
     - Flag indicating if this is the first prompt
   - Returns multiple mask candidates with IOU scores

3. **Mask Selection**:
   - Selects mask with highest IOU score
   - Updates `prompt_mask` for next iteration
   - Converts boolean mask to point indices

4. **Result Preparation**:
   - Denormalizes segmented point coordinates
   - Converts colors to 0-255 range
   - Returns segment data including:
     - Point indices in original point cloud
     - Original coordinates of segmented points
     - Colors of segmented points
     - IOU score
     - Total number of points

### API Endpoints

#### POST `/load_3d_model`
Loads a 3D model for segmentation.

**Request Body**:
```json
{
  "model_id": "uuid-string"
}
```

**Response**:
```json
{
  "success": true,
  "model_id": "uuid-string",
  "glb_path": "path/to/model.glb"
}
```

#### POST `/segment_3d_model`
Performs segmentation with a click point.

**Request Body**:
```json
{
  "x": 0.5,
  "y": 0.3,
  "z": -0.2,
  "prompt_label": 1
}
```

**Response**:
```json
{
  "success": true,
  "segment": {
    "segment_id": 0,
    "point_indices": [1, 5, 10, ...],
    "num_points": 1234,
    "iou_score": 0.85,
    "points": [[x1, y1, z1], ...],
    "colors": [[r1, g1, b1], ...],
    "model_id": "uuid-string"
  },
  "mask": [true, false, true, ...],
  "total_points": 10000,
  "model_id": "uuid-string"
}
```

#### POST `/clear_3d_prompts`
Clears accumulated prompts for iterative refinement.

**Response**:
```json
{
  "success": true,
  "message": "Prompts cleared"
}
```

#### GET `/get_pointcloud`
Retrieves point cloud data for visualization (currently not used in frontend).

**Response**:
```json
{
  "success": true,
  "xyz": [x1, y1, z1, x2, y2, z2, ...],
  "rgb": [r1, g1, b1, r2, g2, b2, ...],
  "num_points": 10000,
  "model_id": "uuid-string"
}
```

## Frontend Implementation

### State Management

The frontend maintains several state variables:

- `segmentationMode`: Boolean indicating if segmentation is active
- `current3DSegmentationData`: Object storing current segmentation state and results
- `modelBoundingBox`: THREE.Box3 for click validation
- `raycaster`: THREE.Raycaster for 3D click detection
- `mouse`: THREE.Vector2 for normalized mouse coordinates
- `originalMeshColors`: Backup of original vertex colors
- `originalTextures`: Backup of original material textures

### User Interaction Flow

1. **Enable Segmentation** (`enableSegmentation`):
   - User clicks "Segment 3D Model" button
   - Frontend sends POST request to `/load_3d_model`
   - Backend loads and processes the GLB file
   - Frontend enables segmentation mode
   - UI updates to show segmentation instructions

2. **Click Handling** (`handleModelClick`):
   - User clicks (left or right) on the Three.js canvas
   - Mouse coordinates are normalized to [-1, 1] range
   - Raycaster finds intersection with 3D model
   - If intersection found, calls `handle3DPointClick` with 3D point

3. **Segmentation Request** (`handle3DPointClick`):
   - Sends POST request to `/segment_3d_model` with:
     - 3D coordinates (x, y, z) from raycast intersection
     - Prompt label (1 for left-click, 0 for right-click)
   - Receives segmentation result
   - Calls `applySegmentationToMesh` to visualize result
   - Updates UI with segmentation statistics

4. **Clear Segmentation** (`clearSegmentation`):
   - Sends POST request to `/clear_3d_prompts`
   - Restores original vertex colors
   - Restores original textures
   - Resets segmentation state
   - Updates UI

### Visualization (`applySegmentationToMesh`)

The visualization process maps segmentation results (point cloud indices) to mesh vertices:

1. **Mesh Discovery**:
   - Traverses the 3D model to find all meshes
   - Uses the first mesh (or could be extended to handle multiple meshes)

2. **Color Attribute Setup**:
   - Checks if geometry has color attribute
   - If not, creates default gray colors
   - Stores original colors for restoration

3. **Spatial Mapping**:
   - Calculates mesh bounding box
   - Sets threshold as 5% of largest dimension
   - For each mesh vertex:
     - Calculates distance to each segmented point
     - If within threshold, colors vertex blue
     - Otherwise, restores original color or sets to white

4. **Material Updates**:
   - Enables `vertexColors` on all materials
   - Disables all texture maps (map, normalMap, roughnessMap, etc.)
   - Sets base material color to white (ensures vertex colors are visible)
   - Forces material update

5. **Color Application**:
   - Segmented areas: Blue `[0.2, 0.4, 1.0]`
   - Non-segmented areas: Original colors or white

### Coordinate Transformations

The system handles coordinate transformations between different spaces:

1. **Screen to Normalized Device Coordinates (NDC)**:
   - Mouse click (pixels) → normalized [-1, 1] range
   - Formula: `x = (clientX - rect.left) / rect.width * 2 - 1`
   - Formula: `y = -(clientY - rect.top) / rect.height * 2 + 1`

2. **NDC to 3D World Coordinates**:
   - Raycaster uses camera and mouse coordinates
   - Finds intersection with 3D model
   - Returns 3D point in world space

3. **World Coordinates to Point-SAM Normalized**:
   - Backend normalizes using: `(point - shift) / scale`
   - Shift is mean of point cloud
   - Scale is maximum distance from center

4. **Point-SAM Normalized to Original**:
   - Denormalizes using: `point * scale + shift`
   - Used when returning segmented point coordinates

5. **Point Cloud to Mesh Vertices**:
   - Uses spatial proximity mapping
   - Threshold-based distance calculation
   - Maps segmented points to nearest mesh vertices

## Data Flow

```
User Click (Screen)
    ↓
Mouse Coordinates (Normalized)
    ↓
Raycaster (3D Intersection)
    ↓
3D Point (World Coordinates)
    ↓
POST /segment_3d_model
    ↓
Backend: Normalize Coordinates
    ↓
Point-SAM Inference
    ↓
Segmentation Mask (Point Indices)
    ↓
Denormalize Segmented Points
    ↓
Return to Frontend
    ↓
Spatial Mapping (Points → Vertices)
    ↓
Vertex Color Update
    ↓
Visualization (Blue Segmented Areas)
```

## Iterative Refinement

The system supports iterative refinement:

1. **First Click**: Creates initial segmentation mask
2. **Subsequent Clicks**: 
   - Accumulates prompts (positive and negative)
   - Uses previous mask as input to Point-SAM
   - Refines segmentation based on new prompts
3. **Clear**: Resets all prompts and mask

The `current_ply_data` dictionary maintains:
- `prompts`: List of all click points (normalized)
- `labels`: List of prompt labels (1 or 0)
- `prompt_mask`: Previous segmentation mask (for refinement)

## Error Handling

### Backend Errors

- **Point-SAM Not Available**: Returns 503 status with error message
- **Model Not Found**: Returns 200 status with error in JSON body
- **GLB Loading Failure**: Returns error message
- **Segmentation Failure**: Returns error with appropriate status code
- **Segment Too Small**: Returns 400 status if segment has <= 10 points

### Frontend Errors

- **No Model Generated**: Shows error if segmentation attempted before generation
- **Click Miss**: Logs message if click doesn't intersect model
- **Network Errors**: Catches and displays fetch errors
- **Segmentation Errors**: Shows error message to user

## Technical Details

### Point Sampling

- Default: 10,000 points sampled from mesh surface
- Uses trimesh's `sample()` method
- Returns both points and face indices
- Colors extracted from face or vertex colors if available

### Normalization

- Centers point cloud at origin
- Scales to unit sphere (maximum distance = 1.0)
- Preserves aspect ratio
- Essential for Point-SAM input requirements

### Material Handling

- Stores original textures before segmentation
- Disables textures during segmentation (vertex colors take priority)
- Restores textures when clearing segmentation
- Handles both single materials and material arrays

### Performance Considerations

- Spatial mapping uses threshold-based early exit
- Could be optimized with spatial hash or KD-tree
- Point-SAM inference runs on GPU (CUDA)
- Frontend updates are synchronous but fast

## Dependencies

### Backend
- Point-SAM model and checkpoint
- PyTorch (with CUDA)
- trimesh
- numpy
- scipy
- safetensors
- hydra-core
- omegaconf
- NVIDIA Apex
- torkit3d

### Frontend
- Three.js (r128)
- GLTFLoader
- OrbitControls