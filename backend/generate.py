#!/usr/bin/env python3
"""
InstructMesh-PhysiOpt-Integration - 3D Generation Module
Handles image-to-3D and text-to-3D conversion using TRELLIS pipeline
Based on trellis-physics-studio/source/sample.py structure
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Add TRELLIS to the path
sys.path.append("/home/farazfaruqi/trellis-physics")

# Set environment variables for TRELLIS
os.environ["SPCONV_ALGO"] = "native"  # Can be 'native' or 'auto', default is 'auto'.
# 'auto' is faster but will do benchmarking at the beginning.
# Recommended to set to 'native' if run only once.
# Use default attention backend from TRELLIS environment (flash-attn or xformers)
# os.environ['ATTN_BACKEND'] = 'xformers'  # Uncomment to force xformers

import imageio
from PIL import Image
import trimesh
import torch
from trellis.pipelines import TrellisTextTo3DPipeline, TrellisImageTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils
from trellis.modules import sparse as sp
from trellis.modules.sparse.basic import save_slat_conds
from trellis.utils.phys_utils import *
from trellis.utils import postprocessing_utils

# Global pipeline cache
_text_pipeline = None
_image_pipeline = None

def load_text_pipeline():
    """Load and cache the text-to-3D pipeline"""
    global _text_pipeline
    if _text_pipeline is None:
        print("Loading TRELLIS text-to-3D pipeline...")
        _text_pipeline = TrellisTextTo3DPipeline.from_pretrained(
            "JeffreyXiang/TRELLIS-text-xlarge"
        )
        if torch.cuda.is_available():
            _text_pipeline.cuda()
        print("Text-to-3D pipeline loaded successfully!")
    return _text_pipeline

def load_image_pipeline():
    """Load and cache the image-to-3D pipeline"""
    global _image_pipeline
    if _image_pipeline is None:
        print("Loading TRELLIS image-to-3D pipeline...")
        _image_pipeline = TrellisImageTo3DPipeline.from_pretrained(
            "JeffreyXiang/TRELLIS-image-large"
        )
        if torch.cuda.is_available():
            _image_pipeline.cuda()
        print("Image-to-3D pipeline loaded successfully!")
    return _image_pipeline

def clear_pipeline_cache():
    """
    Clear cached pipelines from GPU memory.
    Moves pipelines to CPU and clears references to free GPU memory.
    """
    global _text_pipeline, _image_pipeline
    
    if torch.cuda.is_available():
        if _text_pipeline is not None:
            try:
                _text_pipeline.cpu()
                print("[MEMORY] Text pipeline moved to CPU")
            except Exception as e:
                print(f"[MEMORY] Warning: Could not move text pipeline to CPU: {e}")
            _text_pipeline = None
        
        if _image_pipeline is not None:
            try:
                _image_pipeline.cpu()
                print("[MEMORY] Image pipeline moved to CPU")
            except Exception as e:
                print(f"[MEMORY] Warning: Could not move image pipeline to CPU: {e}")
            _image_pipeline = None
        
        # Clear CUDA cache
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
        print("[MEMORY] Pipeline cache cleared")

def sample(out_folder, text=None, image=None, seed=1, mesh=True, rf=False, no_slat=False, save_video=False, n_samples=1):
    """
    Run sampling as a function, based on trellis-physics-studio/source/sample.py.
    This function saves all relevant data for downstream tasks including SLAT files.
    
    Args:
        out_folder: Output directory for generated files
        text: Text prompt (if text-to-3D)
        image: Image path (if image-to-3D)
        seed: Random seed for generation
        mesh: Whether to generate mesh outputs
        rf: Whether to generate radiance field outputs
        no_slat: If True, skip SLAT file generation (default: False - always save SLAT for downstream tasks)
        save_video: Whether to save video renders
        n_samples: Number of samples to generate
    
    Returns:
        Dictionary with file paths and metadata
    """
    with torch.no_grad():
        # Load a pipeline from a model folder or a Hugging Face model hub.
        if image:
            pipeline = load_image_pipeline()
        else:
            pipeline = load_text_pipeline()
        
        # Prepare formats to return
        formats = ["gaussian"]
        if rf:
            formats.append("radiance_field")
        if mesh:
            formats.append("mesh")
        if not no_slat:
            formats.append("slat")

        # Run the pipeline
        outputs = pipeline.run(
            Image.open(image) if image else text,
            seed=seed,
            # Optional parameters
            # sparse_structure_sampler_params={
            #     "steps": 12,
            #     "cfg_strength": 7.5,
            # },
            # slat_sampler_params={
            #     "steps": 12,
            #     "cfg_strength": 7.5,
            # },
            formats=formats,
            num_samples=n_samples,
        )
        # outputs is a dictionary containing generated 3D assets in different formats:
        # - outputs['gaussian']: a list of 3D Gaussians
        # - outputs['radiance_field']: a list of radiance fields
        # - outputs['mesh']: a list of meshes
        # - outputs['slat']: a list of sparse latent tensors (for physics simulation)

        os.makedirs(out_folder, exist_ok=True)

        # If it's an image, copy it. If it's a text, write it.
        if image:
            _, ext_image = os.path.splitext(image)
            shutil.copy(image, os.path.join(out_folder, "image" + ext_image))
        else:
            # Save text prompt
            with open(os.path.join(out_folder, "prompt.txt"), "w") as f:
                f.write(text)

        saved_files = {}
        
        for i_sample in range(n_samples):
            sample_files = {}

            # Render/export visualization of the outputs
            if save_video:
                video = render_utils.render_video(outputs["gaussian"][i_sample])["color"]
                video_path = os.path.join(out_folder, f"sample_gs_{i_sample:02d}.mp4")
                imageio.mimsave(video_path, video, fps=30)
                sample_files["gaussian_video"] = video_path
                
            if rf:
                if save_video:
                    video = render_utils.render_video(outputs["radiance_field"][i_sample])["color"]
                    video_path = os.path.join(out_folder, f"sample_rf_{i_sample:02d}.mp4")
                    imageio.mimsave(video_path, video, fps=30)
                    sample_files["radiance_field_video"] = video_path
                    
            if mesh:
                if save_video:
                    video = render_utils.render_video(outputs["mesh"][i_sample])["normal"]
                    video_path = os.path.join(out_folder, f"sample_mesh_{i_sample:02d}.mp4")
                    imageio.mimsave(video_path, video, fps=30)
                    sample_files["mesh_video"] = video_path

                # Export OBJ file
                mesh_obj = trimesh.Trimesh(
                    vertices=outputs["mesh"][i_sample].vertices.cpu().numpy(),
                    faces=outputs["mesh"][i_sample].faces.cpu().numpy(),
                )
                obj_path = os.path.join(out_folder, f"sample_{i_sample:02d}.obj")
                mesh_obj.export(obj_path)
                sample_files["mesh_obj"] = obj_path

                # GLB files can be extracted from the outputs
                try:
                    glb = postprocessing_utils.to_glb(
                        outputs["gaussian"][i_sample],
                        outputs["mesh"][i_sample],
                        # Optional parameters
                        simplify=0.95,  # Ratio of triangles to remove in the simplification process
                        texture_size=1024,  # Size of the texture used for the GLB
                        y_up=False,
                    )
                    glb_path = os.path.join(out_folder, f"sample_{i_sample:02d}.glb")
                    glb.export(glb_path)
                    sample_files["mesh_glb"] = glb_path
                except Exception as e:
                    print(f"Failed to export GLB file: {e}")

            # Save Gaussians as PLY files
            ply_path = os.path.join(out_folder, f"sample_{i_sample:02d}.ply")
            outputs["gaussian"][i_sample].save_ply(ply_path)
            sample_files["gaussian_ply"] = ply_path

            # Save SLAT files for downstream physics tasks (critical for physics optimization)
            if not no_slat:
                slat: sp.SparseTensor = outputs["slat"][i_sample]
                cond: torch.Tensor = outputs["cond"]
                neg_cond: torch.Tensor = outputs["neg_cond"]
                z_s: torch.Tensor = outputs["z_s"][i_sample]
                slat_path = os.path.join(out_folder, f"slat_{i_sample:02d}.pt")
                save_slat_conds(slat_path, slat, cond, neg_cond, z_s)
                sample_files["slat"] = slat_path
            
            saved_files[f"sample_{i_sample:02d}"] = sample_files
        
        return {
            "output_folder": out_folder,
            "samples": saved_files,
            "n_samples": n_samples,
            "seed": seed,
            "has_text": text is not None,
            "has_image": image is not None
        }

def generate_3d_from_image(
    image_path: str,
    output_folder: str,
    seed: int = 1,
    num_samples: int = 1,
    save_video: bool = False
) -> Dict[str, Any]:
    """
    Generate 3D models from an image using TRELLIS
    Saves all relevant data for downstream tasks including PLY, OBJ, GLB, and SLAT files.
    
    Args:
        image_path: Path to input image
        output_folder: Directory to save outputs
        seed: Random seed for generation
        num_samples: Number of samples to generate
        save_video: Whether to save video renders
    
    Returns:
        Dictionary containing generated file paths and metadata
    """
    print(f"[GENERATE] Starting image-to-3D generation for: {image_path}")
    
    try:
        results = sample(
            out_folder=output_folder,
            text=None,
            image=image_path,
            seed=seed,
            mesh=True,
            rf=False,
            no_slat=False,  # Always save SLAT for downstream tasks
            save_video=save_video,
            n_samples=num_samples
        )
        
        # For compatibility with existing API, also return GLB path from first sample
        if num_samples > 0 and "sample_00" in results["samples"]:
            sample_00_files = results["samples"]["sample_00"]
            results["glb_path"] = sample_00_files.get("mesh_glb")
            results["obj_path"] = sample_00_files.get("mesh_obj")
            results["ply_path"] = sample_00_files.get("gaussian_ply")
            results["slat_path"] = sample_00_files.get("slat")
            results["success"] = True
        else:
            results["success"] = False
            results["error"] = "No samples generated"
        
        print(f"[GENERATE] Generation completed! Files saved in: {output_folder}")
        return results
        
    except Exception as e:
        print(f"[GENERATE] Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "output_folder": output_folder
        }
