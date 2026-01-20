#!/usr/bin/env python3
"""
3D Model Segmentation Module using Point-SAM
Handles all segmentation-related functionality
"""

import sys
import os
import numpy as np
import torch
import trimesh
from scipy.spatial.distance import cdist
from pathlib import Path

# Add Point-SAM to the path
sys.path.append("/home/farazfaruqi/Point-SAM/")
sys.path.append("/home/farazfaruqi/Point-SAM/third_party/torkit3d/")

# Point-SAM initialization
POINT_SAM_AVAILABLE = False
point_sam_model = None
current_ply_data = None

try:
    from pc_sam.model.pc_sam import PointCloudSAM
    from pc_sam.utils.torch_utils import replace_with_fused_layernorm
    from safetensors.torch import load_model
    import hydra
    from omegaconf import OmegaConf
    
    def initialize_point_sam():
        """Initialize Point-SAM model"""
        config_dir = "../../Point-SAM/configs"
        checkpoint_path = "/home/farazfaruqi/Point-SAM/checkpoints/model.safetensors"
        
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Point-SAM requires CUDA.")
        
        # Clear any existing hydra instance
        if hydra.core.global_hydra.GlobalHydra.instance().is_initialized():
            hydra.core.global_hydra.GlobalHydra.instance().clear()
        
        with hydra.initialize(config_path=config_dir, version_base=None):
            cfg = hydra.compose(config_name="large")
            OmegaConf.resolve(cfg)
            
            model = hydra.utils.instantiate(cfg.model)
            model.apply(replace_with_fused_layernorm)
            load_model(model, checkpoint_path)
            model.eval()
            model.cuda()
            
            return model
    
    # Initialize Point-SAM on module import
    try:
        point_sam_model = initialize_point_sam()
        POINT_SAM_AVAILABLE = True
    except Exception as e:
        POINT_SAM_AVAILABLE = False
        point_sam_model = None

except Exception as e:
    POINT_SAM_AVAILABLE = False
    point_sam_model = None


def load_glb_for_point_sam(glb_path, num_samples=10000):
    """Load GLB file and prepare it for Point-SAM"""
    try:
        mesh = trimesh.load(glb_path)
        
        # Handle Scene vs Mesh
        if hasattr(mesh, 'geometry'):
            meshes = []
            for geom in mesh.geometry.values():
                if hasattr(geom, 'vertices') and hasattr(geom, 'faces'):
                    meshes.append(geom)
            
            if not meshes:
                raise ValueError("No valid mesh geometry found in GLB file")
            
            if len(meshes) == 1:
                mesh = meshes[0]
            else:
                mesh = trimesh.util.concatenate(meshes)
        
        # Sample points from mesh surface
        points, face_indices = mesh.sample(num_samples, return_index=True)
        
        # Extract colors if available
        if hasattr(mesh.visual, 'face_colors') and mesh.visual.face_colors is not None:
            colors = mesh.visual.face_colors[face_indices][:, :3]
        elif hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
            distances = cdist(points, mesh.vertices)
            nearest_vertex_indices = np.argmin(distances, axis=1)
            colors = mesh.visual.vertex_colors[nearest_vertex_indices][:, :3]
        else:
            colors = np.full((len(points), 3), 128.0)
        
        # Normalize colors to [0,1] range if needed
        if colors.max() > 1.0:
            colors = colors / 255.0
        
        # Apply Point-SAM normalization
        xyz = points.astype(np.float32)
        rgb = colors.astype(np.float32)
        
        shift = xyz.mean(0)
        scale = np.linalg.norm(xyz - shift, axis=-1).max()
        xyz_normalized = (xyz - shift) / scale
        
        return xyz_normalized.astype(np.float32), rgb.astype(np.float32), shift, scale
            
    except Exception as e:
        return None, None, None, None


def load_model_for_segmentation(model_dir, files_dir):
    """Load a 3D model for segmentation"""
    global current_ply_data
    
    if not POINT_SAM_AVAILABLE:
        return None, "Point-SAM not available"
    
    # Find GLB file
    glb_path = None
    for glb_name in ["model.glb", "sample_00.glb"]:
        candidate = files_dir / model_dir / glb_name
        if candidate.exists():
            glb_path = candidate
            break
    
    if glb_path is None:
        glb_files = list((files_dir / model_dir).glob("*.glb"))
        if glb_files:
            glb_path = glb_files[0]
        else:
            return None, f"GLB file not found for model {model_dir}"
    
    # Load GLB
    points_norm, colors_norm, shift, scale = load_glb_for_point_sam(str(glb_path))
    
    if points_norm is None or colors_norm is None:
        return None, "Failed to load GLB data"
    
    # Convert to PyTorch tensors
    pc_xyz = torch.from_numpy(points_norm).cuda().float().unsqueeze(0)
    pc_rgb = torch.from_numpy(colors_norm).cuda().float().unsqueeze(0)
    
    # Store model data
    current_ply_data = {
        'pc_xyz': pc_xyz,
        'pc_rgb': pc_rgb,
        'shift': shift,
        'scale': scale,
        'model_id': model_dir,
        'glb_path': str(glb_path),
        'prompts': [],
        'labels': [],
        'prompt_mask': None
    }
    
    return current_ply_data, None


def clear_prompts():
    """Clear accumulated prompts"""
    global current_ply_data
    if current_ply_data is not None:
        current_ply_data['prompts'] = []
        current_ply_data['labels'] = []
        current_ply_data['prompt_mask'] = None


def get_pointcloud_data():
    """Get point cloud data for visualization"""
    global current_ply_data
    if current_ply_data is None:
        return None, "No 3D model loaded"
    
    try:
        pc_xyz_cpu = current_ply_data['pc_xyz'][0].cpu().numpy()
        pc_rgb_cpu = current_ply_data['pc_rgb'][0].cpu().numpy()
        shift = current_ply_data['shift']
        scale = current_ply_data['scale']
        
        # Denormalize points
        pc_xyz_orig = pc_xyz_cpu * scale + shift
        
        # Flatten for Three.js
        positions = pc_xyz_orig.flatten().tolist()
        colors = pc_rgb_cpu.flatten().tolist()
        
        return {
            "xyz": positions,
            "rgb": colors,
            "num_points": len(pc_xyz_orig),
            "model_id": current_ply_data['model_id']
        }, None
    except Exception as e:
        return None, str(e)


def segment_with_click(click_point):
    """Perform segmentation with click point"""
    global current_ply_data
    
    if not POINT_SAM_AVAILABLE:
        return None, "Point-SAM not available"
    
    if current_ply_data is None:
        return None, "No 3D model loaded"
    
    try:
        pc_xyz = current_ply_data['pc_xyz']
        pc_rgb = current_ply_data['pc_rgb']
        shift = current_ply_data['shift']
        scale = current_ply_data['scale']
        model_id = current_ply_data['model_id']
        
        # Get prompt label (1 = positive, 0 = negative)
        prompt_label = click_point.get('prompt_label', 1)
        
        # Convert click point to normalized coordinates
        if 'x' in click_point and 'y' in click_point and 'z' in click_point:
            click_pos = np.array([click_point['x'], click_point['y'], click_point['z']])
            click_pos_norm = (click_pos - shift) / scale
            prompt_point = click_pos_norm.reshape(1, 3)
        else:
            center_point = pc_xyz[0].mean(dim=0).cpu().numpy()
            prompt_point = center_point.reshape(1, 3)
        
        # Add to prompts list
        current_ply_data['prompts'].append(prompt_point[0])
        current_ply_data['labels'].append(prompt_label)
        
        # Convert accumulated prompts to tensors
        prompt_points = torch.from_numpy(np.array(current_ply_data['prompts'])).cuda().float().unsqueeze(0)
        prompt_labels = torch.from_numpy(np.array(current_ply_data['labels'])).cuda().unsqueeze(0)
        
        # Run Point-SAM prediction
        with torch.no_grad():
            masks, iou_preds = point_sam_model.predict_masks(
                pc_xyz, pc_rgb, prompt_points, prompt_labels, 
                current_ply_data['prompt_mask'], 
                current_ply_data['prompt_mask'] is None
            )
        
        # Use mask with highest IOU
        best_idx = torch.argmax(iou_preds[0])
        current_ply_data['prompt_mask'] = masks[0][best_idx].unsqueeze(0)
        segment_mask = masks[0][best_idx] > 0
        iou_score = iou_preds[0][best_idx].item()
        
        # Convert mask to point indices
        point_indices = torch.where(segment_mask)[0].cpu().numpy().tolist()
        
        if len(point_indices) <= 10:
            return None, f"Segment too small: only {len(point_indices)} points"
        
        # Get original coordinates for segmented points
        pc_xyz_cpu = pc_xyz[0].cpu().numpy()
        pc_rgb_cpu = pc_rgb[0].cpu().numpy()
        
        segment_points_norm = pc_xyz_cpu[point_indices]
        segment_colors = pc_rgb_cpu[point_indices]
        segment_points_orig = segment_points_norm * scale + shift
        
        segment_colors_255 = (segment_colors * 255).astype(np.uint8)
        
        segment = {
            "segment_id": 0,
            "point_indices": point_indices,
            "num_points": len(point_indices),
            "iou_score": float(iou_score),
            "points": segment_points_orig.tolist(),
            "colors": segment_colors_255.tolist(),
            "model_id": model_id
        }
        
        return {
            "segment": segment,
            "mask": segment_mask.cpu().numpy().tolist(),
            "total_points": pc_xyz.shape[1],
            "model_id": model_id
        }, None
        
    except Exception as e:
        return None, str(e)
