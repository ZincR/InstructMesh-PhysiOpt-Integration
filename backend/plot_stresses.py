import numpy as np
import matplotlib.pyplot as plt
import os
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def plot_hexahedral_mesh_surface_stylized(
    elements,
    nodes,
    values,
    folder_path,
    cmap='coolwarm',  # or try 'winter', 'Greens'
    alpha=0.5,
    optimized=False,
    normalize=True,
):
    """
    Stylized surface visualization of a hexahedral mesh with stress values.

    normalize: If True (default), clamp values to [0, 1] and use vmin=0, vmax=1.
               If False, use raw values and data-derived vmin/vmax for the colormap.
    """

    hex_faces = [
        [0, 1, 2, 3], [4, 5, 6, 7],
        [0, 1, 5, 4], [1, 2, 6, 5],
        [2, 3, 7, 6], [3, 0, 4, 7],
    ]

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    face_verts = []
    face_colors = []
    seen_faces = set()

    for elem_idx, elem in enumerate(elements):
        val = values[elem_idx]
        norm_val = min(val, 1.0) if normalize else val

        for face in hex_faces:
            face_nodes = tuple(sorted([elem[i] for i in face]))

            if face_nodes in seen_faces:
                continue
            seen_faces.add(face_nodes)

            verts = [nodes[elem[i]] for i in face]
            face_verts.append(verts)
            face_colors.append(norm_val)

    # Colormap
    if normalize:
        vmin, vmax = 0.0, 1.0
        cbar_label = "Stress / Max Stress"
    else:
        face_arr = np.asarray(face_colors)
        vmin, vmax = float(face_arr.min()), float(face_arr.max())
        if vmin == vmax:
            vmax = vmin + 1.0
        cbar_label = "Stress (raw)"
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    colormap = plt.cm.get_cmap(cmap)
    color_mapped = colormap(norm(face_colors))

    # Plot stylized mesh
    collection = Poly3DCollection(
        face_verts,
        facecolors=color_mapped,
        edgecolors='gray',   # lighter edges
        linewidths=0.1,
        alpha=alpha
    )
    ax.add_collection3d(collection)

    # Set axis
    ax.set_xlim(nodes[:, 0].min(), nodes[:, 0].max())
    ax.set_ylim(nodes[:, 1].min(), nodes[:, 1].max())
    ax.set_zlim(nodes[:, 2].min(), nodes[:, 2].max())
    ax.set_box_aspect([1, 1, 1])
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.title(f"Stress Visualization {'Optimized' if optimized else 'Initial'}")

    # Colorbar
    mappable = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
    mappable.set_array([])
    plt.colorbar(mappable, ax=ax, shrink=0.6, pad=0.1, label=cbar_label)

    plt.savefig(os.path.join(folder_path, "stresses_optimized.png" if optimized else "stresses.png"))