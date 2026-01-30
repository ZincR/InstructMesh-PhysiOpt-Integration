#!/usr/bin/env python3
"""
InstructMesh-PhysiOpt-Integration - Physics Optimization Module
Handles physics-based optimization of 3D models using TRELLIS physics engine
Based on trellis-physics-studio/source/optimize.py
"""

import os
import sys
import gc
from pathlib import Path
from typing import Dict, Any, Optional
from plot_stresses import plot_hexahedral_mesh_surface_stylized

# Add TRELLIS to the path
sys.path.append("/home/farazfaruqi/trellis-physics")

# Set environment variables for TRELLIS
os.environ["SPCONV_ALGO"] = "native"
# Use default attention backend from TRELLIS environment (flash-attn or xformers)
# os.environ['ATTN_BACKEND'] = 'xformers'  # Uncomment to force xformers

# Set PyTorch CUDA memory allocation config to reduce fragmentation
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from trellis.utils import postprocessing_utils
from trellis.modules.sparse.basic import SlatPayload
from trellis.physics.optimizer_factory import OptimizerFactory
from trellis.physics.boundary import get_directional_boundary_conditions
from trellis.utils.phys_utils import *
from trellis.representations.mesh.cube2mesh import MeshExtractResult


def clear_cuda_memory(aggressive=False):
    """
    Clear CUDA memory cache and run garbage collection.
    This should be called before optimization to free up GPU memory.
    
    Args:
        aggressive: If True, perform more aggressive memory clearing including
                    resetting PyTorch's memory pool
    """
    print("[MEMORY] Clearing CUDA memory...")
    
    if torch.cuda.is_available():
        # Get memory stats before clearing
        allocated_before = torch.cuda.memory_allocated() / 1024**3  # GB
        reserved_before = torch.cuda.memory_reserved() / 1024**3  # GB
        
        print(f"[MEMORY] Before clearing - Allocated: {allocated_before:.2f} GB, Reserved: {reserved_before:.2f} GB")
        
        # Clear cached pipelines from GPU memory
        try:
            from generate import clear_pipeline_cache
            clear_pipeline_cache()
        except Exception as e:
            print(f"[MEMORY] Note: Could not clear pipeline cache: {e}")
            # Continue anyway - we'll still clear CUDA cache
        
        # Run garbage collection multiple times for thorough cleanup
        for i in range(3):
            gc.collect()
        
        # Clear CUDA cache
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
        # Aggressive memory clearing
        if aggressive:
            print("[MEMORY] Performing aggressive memory clearing...")
            # Reset PyTorch's memory pool
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()
            gc.collect()
            
            # Try to reset memory stats if possible
            if hasattr(torch.cuda, 'reset_peak_memory_stats'):
                torch.cuda.reset_peak_memory_stats()
        
        # Get memory stats after clearing
        allocated_after = torch.cuda.memory_allocated() / 1024**3  # GB
        reserved_after = torch.cuda.memory_reserved() / 1024**3  # GB
        
        freed = (allocated_before - allocated_after)
        print(f"[MEMORY] After clearing - Allocated: {allocated_after:.2f} GB, Reserved: {reserved_after:.2f} GB")
        print(f"[MEMORY] Freed: {freed:.2f} GB")
        
        # Warn if memory is still high
        if reserved_after > 1.0:
            print(f"[MEMORY] WARNING: Reserved memory is still high ({reserved_after:.2f} GB). "
                  "This may cause OOM during optimization.")
    else:
        print("[MEMORY] CUDA not available, skipping memory clearing")


def optimize_model(
    folder_path: str,
    save_slat: bool = False
) -> Dict[str, Any]:
    """
    Optimize a 3D model using physics simulation.
    
    Args:
        folder_path: Path to folder containing slat_00.pt file
        save_slat: Whether to save optimizer states as .pt file
    
    Returns:
        Dictionary with optimization results and file paths
    """
    folder = Path(folder_path)
    
    # Check if SLAT file exists
    slat_file = folder / "slat_00.pt"
    if not slat_file.exists():
        raise FileNotFoundError(f"SLAT file not found: {slat_file}")
    
    print(f"[OPTIMIZE] Starting physics optimization for: {folder}")
    
    # Clear CUDA memory aggressively before optimization to avoid OOM errors
    clear_cuda_memory(aggressive=True)
    
    try:
        # 1. Load SLAT payload
        slat = SlatPayload.from_path(str(slat_file))
        print("[OPTIMIZE] SLAT payload loaded successfully")
        
        # 2. Create OptimizerFactory
        optimizer_factory = OptimizerFactory(slat)
        print("[OPTIMIZE] Optimizer factory initiated")
        
        # 3. Get simulation voxels and set boundary conditions
        coarse_coords, nodes, elements = optimizer_factory.get_simulation_voxels()
        
        # Set bottom boundary conditions (supports the model from bottom)
        bottom_boundary_conditions = get_directional_boundary_conditions(
            nodes, direction="bottom_z", threshold=0.05
        )
        optimizer_factory.set_boundary_conditions(bottom_boundary_conditions)
        print("[OPTIMIZE] Boundary conditions set (bottom support)")
        
        # 4. Create optimizer
        optimizer = optimizer_factory.create_optimizer()
        print(f"[OPTIMIZE] Optimizer created. Coords shape: {slat.slat.coords.shape}")
        print(f"[OPTIMIZE] Sparse coords shape: {optimizer.current_trajectory.states[0].coarse_coords.shape}")
        
        # Final memory clear before optimization starts (after optimizer creation)
        if torch.cuda.is_available():
            allocated_before_opt = torch.cuda.memory_allocated() / 1024**3
            reserved_before_opt = torch.cuda.memory_reserved() / 1024**3
            print(f"[MEMORY] Before optimization - Allocated: {allocated_before_opt:.2f} GB, Reserved: {reserved_before_opt:.2f} GB")
            
            # Clear any remaining cached memory
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            allocated_after_opt = torch.cuda.memory_allocated() / 1024**3
            reserved_after_opt = torch.cuda.memory_reserved() / 1024**3
            print(f"[MEMORY] After final clear - Allocated: {allocated_after_opt:.2f} GB, Reserved: {reserved_after_opt:.2f} GB")
        
        # 5. Run optimization
        print("[OPTIMIZE] Running physics optimization...")
        try:
            optimizer.optimize()
            print("[OPTIMIZE] Optimization completed successfully")
        except RuntimeError as e:
            print(f"[OPTIMIZE] Optimization failed: {e}")
            raise RuntimeError(f"Physics optimization failed: {str(e)}")
        
        # 6. Save optimizer states as .pt (optional)
        if save_slat:
            slat_dest = folder / "slat_optim_states.pt"
            torch.save({"optimizer_states": optimizer.current_trajectory.states}, str(slat_dest))
            print(f"[OPTIMIZE] Optimizer states saved to: {slat_dest}")
        
        # 7. Save optimized GLB
        print("[OPTIMIZE] Exporting optimized GLB file...")
        glb_path = folder / "sample_optimized.glb"
        
        glb = postprocessing_utils.to_glb(
            optimizer.current_trajectory.states[-1].splats.to(device="cuda"),
            MeshExtractResult(
                torch.tensor(optimizer.current_trajectory.states[-1].mesh_vertices),
                torch.tensor(optimizer.current_trajectory.states[-1].mesh_faces)
            ),
            simplify=0.95,
            texture_size=1024,
            y_up=False,
        )
        
        glb.export(str(glb_path))
        print(f"[OPTIMIZE] Optimized GLB saved to: {glb_path}")

        #8. Plot stresses
        initial_mises = optimizer.current_trajectory.states[0].mises
        initial_nodes = optimizer.current_trajectory.states[0].nodes
        initial_elements = optimizer.current_trajectory.states[0].elements

        plot_hexahedral_mesh_surface_stylized(
            initial_elements,
            initial_nodes,
            initial_mises,
            folder_path,
            optimized=False,
            normalize=False
        )

        optimized_mises = optimizer.current_trajectory.states[-1].mises
        optimized_nodes = optimizer.current_trajectory.states[-1].nodes
        optimized_elements = optimizer.current_trajectory.states[-1].elements

        plot_hexahedral_mesh_surface_stylized(
            optimized_elements,
            optimized_nodes,
            optimized_mises,
            folder_path,
            optimized=True,
            normalize=False
        )
        
        print("[OPTIMIZE] Stresses plotted successfully")
        
        # Clean up optimizer and intermediate variables to free memory
        del optimizer
        del optimizer_factory
        del slat
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return {
            "success": True,
            "optimized_glb_path": str(glb_path),
            "folder": str(folder),
            "message": "Physics optimization completed successfully"
        }
        
    except Exception as e:
        print(f"[OPTIMIZE] Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "folder": str(folder)
        }

