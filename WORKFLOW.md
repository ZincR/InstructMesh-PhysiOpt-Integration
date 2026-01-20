# InstructMesh-PhysiOpt-Integration Workflow

This document describes the complete workflow for generating a 3D model from a text prompt and optimizing it using physics simulation.

## Complete Workflow: Text Prompt → Generation → Optimization

### Phase 1: Text-to-3D Generation

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. API Endpoint: POST /generate_from_text                      │
│    File: backend/app.py (lines 150-200)                        │
│    Function: generate_from_text(request: TextRequest)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Create Unique Generation Folder                              │
│    - Generate UUID (generation_id)                             │
│    - Create folder: results/models/{generation_id}/            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Call Generation Function                                     │
│    File: backend/generate.py (lines 240-299)                   │
│    Function: generate_3d_from_text()                           │
│    └─> Calls: sample()                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Load Text-to-3D Pipeline                                     │
│    File: backend/generate.py (lines 39-50)                     │
│    Function: load_text_pipeline()                              │
│    └─> TrellisTextTo3DPipeline.from_pretrained(                │
│            "JeffreyXiang/TRELLIS-text-xlarge"                  │
│        )                                                        │
│    └─> Moves pipeline to CUDA if available                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Run Pipeline Generation                                      │
│    File: backend/generate.py (lines 95-238)                    │
│    Function: sample()                                          │
│    └─> pipeline.run(                                           │
│            text=text_prompt,                                   │
│            seed=seed,                                          │
│            formats=["gaussian", "mesh", "slat"],               │
│            num_samples=1                                       │
│        )                                                        │
│                                                                │
│    Pipeline outputs:                                           │
│    - outputs['gaussian']: 3D Gaussians                         │
│    - outputs['mesh']: Mesh representation                      │
│    - outputs['slat']: Sparse Latent Tensor (for physics)      │
│    - outputs['cond']: Condition tensor                         │
│    - outputs['neg_cond']: Negative condition tensor            │
│    - outputs['z_s']: Latent code                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Save Generated Files                                         │
│    File: backend/generate.py (lines 152-238)                   │
│    Function: sample() - File Export Section                    │
│                                                                │
│    For each sample (typically 1):                              │
│    ├─> Save text prompt: prompt.txt                            │
│    ├─> Save mesh as OBJ: sample_00.obj                         │
│    ├─> Save 3D Gaussians as PLY: sample_00.ply                │
│    ├─> Export GLB file: sample_00.glb                          │
│    │   └─> postprocessing_utils.to_glb()                      │
│    └─> Save SLAT file: slat_00.pt                              │
│        └─> save_slat_conds()  # Critical for optimization!    │
│                                                                │
│    Returns dictionary with file paths                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Return API Response                                          │
│    File: backend/app.py (lines 182-195)                        │
│    Returns:                                                     │
│    {                                                            │
│      "success": true,                                          │
│      "generation_id": "...",                                   │
│      "model_url": "/files/.../sample_00.glb",                 │
│      "text_prompt": "...",                                     │
│      "files": {                                                │
│        "glb": "...",                                           │
│        "obj": "...",                                           │
│        "ply": "...",                                           │
│        "slat": "..."  # Required for optimization             │
│      }                                                         │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Physics Optimization

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. API Endpoint: POST /optimize/{generation_id}                │
│    File: backend/app.py (lines 268-314)                        │
│    Function: optimize_3d_model(generation_id: str)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Validate Generation Folder                                   │
│    - Check if folder exists: results/models/{generation_id}/   │
│    - Check if SLAT file exists: slat_00.pt                     │
│      (Required for physics optimization!)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Clear GPU Memory                                             │
│    File: backend/optimize.py (lines 34-94)                     │
│    Function: clear_cuda_memory(aggressive=True)                │
│    └─> clear_pipeline_cache()  # Free generation pipeline     │
│    └─> gc.collect()                                            │
│    └─> torch.cuda.empty_cache()                                │
│    └─> torch.cuda.synchronize()                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Load SLAT Payload                                            │
│    File: backend/optimize.py (lines 97-218)                    │
│    Function: optimize_model()                                  │
│    └─> SlatPayload.from_path("slat_00.pt")                    │
│    Contains:                                                    │
│    - slat: Sparse Latent Tensor                                │
│    - cond: Condition tensor                                    │
│    - neg_cond: Negative condition tensor                       │
│    - z_s: Latent code                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Create Optimizer Factory                                     │
│    File: backend/optimize.py (line 129)                        │
│    └─> OptimizerFactory(slat)                                  │
│                                                                │
│    Get simulation voxels:                                      │
│    └─> optimizer_factory.get_simulation_voxels()              │
│        Returns:                                                 │
│        - coarse_coords: Coarse voxel coordinates               │
│        - nodes: Simulation nodes                               │
│        - elements: Simulation elements                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Set Boundary Conditions                                      │
│    File: backend/optimize.py (lines 136-139)                   │
│    └─> get_directional_boundary_conditions(                    │
│            nodes, direction="bottom_z", threshold=0.05         │
│        )                                                        │
│    └─> optimizer_factory.set_boundary_conditions(              │
│            bottom_boundary_conditions                          │
│        )                                                        │
│    (Supports the model from the bottom)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Create Optimizer                                             │
│    File: backend/optimize.py (line 143)                        │
│    └─> optimizer_factory.create_optimizer()                    │
│                                                                │
│    Optimizer contains:                                         │
│    - current_trajectory: Optimization trajectory               │
│    - states: List of optimization states                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Run Physics Optimization                                     │
│    File: backend/optimize.py (line 165)                        │
│    └─> optimizer.optimize()                                    │
│                                                                │
│    This performs:                                              │
│    - Physics-based simulation                                  │
│    - Iterative optimization                                    │
│    - Updates model geometry for stability                      │
│    - Stores optimization states in trajectory                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Export Optimized Model                                       │
│    File: backend/optimize.py (lines 177-193)                   │
│    └─> postprocessing_utils.to_glb(                            │
│            splats=optimizer.current_trajectory.states[-1]      │
│                .splats.to(device="cuda"),                      │
│            mesh=MeshExtractResult(                             │
│                vertices=optimizer...states[-1].mesh_vertices,  │
│                faces=optimizer...states[-1].mesh_faces         │
│            ),                                                   │
│            simplify=0.95,                                       │
│            texture_size=1024,                                   │
│            y_up=False                                           │
│        )                                                        │
│    └─> glb.export("sample_optimized.glb")                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. Cleanup and Return Response                                 │
│     File: backend/optimize.py (lines 195-208)                  │
│     └─> Delete optimizer, optimizer_factory, slat             │
│     └─> gc.collect()                                           │
│     └─> torch.cuda.empty_cache()                               │
│                                                                │
│     File: backend/app.py (lines 302-309)                       │
│     Returns:                                                    │
│     {                                                           │
│       "success": true,                                         │
│       "generation_id": "...",                                  │
│       "optimized_model_url": "/files/.../sample_optimized.glb",│
│       "message": "Optimization completed successfully"         │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Functions Call Hierarchy

### Generation Workflow Functions:

1. **app.py**
   - `generate_from_text()` (line 151)
     - Calls: `generate_3d_from_text()` from generate.py

2. **generate.py**
   - `generate_3d_from_text()` (line 240)
     - Calls: `sample()` (line 264)
   - `sample()` (line 95)
     - Calls: `load_text_pipeline()` (line 119)
     - Calls: `pipeline.run()` (line 131) - TRELLIS pipeline
     - Calls: `postprocessing_utils.to_glb()` (line 200)
     - Calls: `save_slat_conds()` (line 226)
   - `load_text_pipeline()` (line 39)
     - Creates/returns cached `TrellisTextTo3DPipeline` instance

### Optimization Workflow Functions:

1. **app.py**
   - `optimize_3d_model()` (line 268)
     - Calls: `optimize_model()` from optimize.py

2. **optimize.py**
   - `optimize_model()` (line 97)
     - Calls: `clear_cuda_memory()` (line 121)
     - Calls: `SlatPayload.from_path()` (line 125)
     - Calls: `OptimizerFactory()` (line 129)
     - Calls: `optimizer_factory.get_simulation_voxels()` (line 133)
     - Calls: `get_directional_boundary_conditions()` (line 136)
     - Calls: `optimizer_factory.set_boundary_conditions()` (line 139)
     - Calls: `optimizer_factory.create_optimizer()` (line 143)
     - Calls: `optimizer.optimize()` (line 165)
     - Calls: `postprocessing_utils.to_glb()` (line 181)
   - `clear_cuda_memory()` (line 34)
     - Calls: `clear_pipeline_cache()` from generate.py (line 54)
     - Calls: `gc.collect()`, `torch.cuda.empty_cache()`

## File Outputs

### After Generation:
- `results/models/{generation_id}/prompt.txt` - Original text prompt
- `results/models/{generation_id}/sample_00.obj` - Mesh in OBJ format
- `results/models/{generation_id}/sample_00.ply` - 3D Gaussians in PLY format
- `results/models/{generation_id}/sample_00.glb` - 3D model in GLB format
- `results/models/{generation_id}/slat_00.pt` - **SLAT file (required for optimization)**

### After Optimization:
- `results/models/{generation_id}/sample_optimized.glb` - Optimized 3D model
- `results/models/{generation_id}/slat_optim_states.pt` - (Optional) Optimizer states

## Important Notes

1. **SLAT File is Critical**: The optimization step requires the `slat_00.pt` file generated during the generation phase. This file contains the sparse latent representation needed for physics simulation.

2. **Memory Management**: The optimization phase aggressively clears GPU memory to avoid OOM errors, as physics optimization is memory-intensive.

3. **Boundary Conditions**: The optimizer automatically sets bottom boundary conditions to support the model from below during simulation.

4. **Pipeline Caching**: The text-to-3D pipeline is cached in memory after first load to avoid reloading for subsequent generations.
