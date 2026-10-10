import numpy as np
from skimage import measure
import trimesh

print("[*] Generating Anatomical Human Liver Geometry & Tumor Core...")

# 1. High-resolution 3D grid
x, y, z = np.ogrid[-50:50:100j, -50:50:100j, -50:50:100j]

# 2. Anatomical Human Liver Formulation (Asymmetric Wedge + Dual Lobes + Fossa Indentation)
# Primary Right Lobe
right_lobe = ((x - 8)**2 / 38.0**2) + ((y + 5)**2 / 24.0**2) + ((z - 2)**2 / 20.0**2)
# Tapered Left Lobe
left_lobe = ((x + 18)**2 / 22.0**2) + ((y + 8)**2 / 16.0**2) + ((z - 4)**2 / 14.0**2)

# Combine lobes with anatomical tapering and organ surface curvature
liver_field = np.minimum(right_lobe, left_lobe)
curvature = 1.0 + 0.18 * np.sin(x / 10.0) - 0.12 * np.cos(y / 8.0)
liver_volume = liver_field * curvature

# Extract smooth organ surface using Marching Cubes
verts_liver, faces_liver, normals_liver, _ = measure.marching_cubes(liver_volume, level=1.0)
verts_liver -= verts_liver.mean(axis=0)

# Export Anatomical Liver Mesh
liver_mesh = trimesh.Trimesh(vertices=verts_liver, faces=faces_liver, vertex_normals=normals_liver)
liver_mesh.export("petct_organ_hull.obj")
print(f"[✓] Created Anatomical Liver: petct_organ_hull.obj ({len(verts_liver)} vertices)")

# 3. Malignant Tumor Lesion (Embedded inside Right Lobe parenchyma)
tumor_field = ((x - 10)**2 / 7.0**2) + ((y - 2)**2 / 6.0**2) + ((z - 3)**2 / 6.0**2)
verts_tumor, faces_tumor, normals_tumor, _ = measure.marching_cubes(tumor_field, level=1.0)
verts_tumor -= verts_tumor.mean(axis=0)
verts_tumor += np.array([12.0, -4.0, 3.0])  # Positioned inside the right lobe

tumor_mesh = trimesh.Trimesh(vertices=verts_tumor, faces=faces_tumor, vertex_normals=normals_tumor)
tumor_mesh.export("pet_active_tumor_core.obj")
print(f"[✓] Created Tumor Lesion Core: pet_active_tumor_core.obj ({len(verts_tumor)} vertices)")
