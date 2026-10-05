import numpy as np
from skimage import measure
import trimesh

print("Processing Dual-Modality PET/CT Volumetric Arrays...")

# 1. Define physical space grid in LPS coordinates (mm)
x, y, z = np.ogrid[-30:30:64j, -30:30:64j, -30:30:64j]

# 2. CT Anatomical Channel: Liver parenchyma tissue approximation
ct_density = np.exp(-((x / 22.0)**2 + (y / 16.0)**2 + (z / 20.0)**2))

# 3. PET Functional Channel: Localized hypermetabolic tracer uptake
tumor_pos = (5.0, -2.0, 4.0)
dist_to_hotspot = np.sqrt((x - tumor_pos[0])**2 + (y - tumor_pos[1])**2 + (z - tumor_pos[2])**2)
pet_suv_map = 8.2 * np.exp(-(dist_to_hotspot / 5.0)**2)  # Peak SUV = 8.2

# --- Marching Cubes Extraction ---

# Extract Organ Hull from CT
verts_ct, faces_ct, normals_ct, _ = measure.marching_cubes(ct_density, level=0.25, spacing=(1.0, 1.0, 1.0))
centroid_offset = verts_ct.mean(axis=0)
verts_ct -= centroid_offset

organ_mesh = trimesh.Trimesh(vertices=verts_ct, faces=faces_ct, vertex_normals=normals_ct)
organ_mesh.export("petct_organ_hull.obj")
print(f"Generated CT Organ Hull: petct_organ_hull.obj ({len(verts_ct)} vertices)")

# Extract Active Malignant Core from PET (SUV >= 2.5 cutoff)
suv_cutoff = 2.5
pet_binary_mask = (pet_suv_map >= suv_cutoff).astype(float)

verts_pet, faces_pet, normals_pet, _ = measure.marching_cubes(pet_binary_mask, level=0.5, spacing=(1.0, 1.0, 1.0))
verts_pet -= centroid_offset + np.array(tumor_pos)

tumor_mesh = trimesh.Trimesh(vertices=verts_pet, faces=faces_pet, vertex_normals=normals_pet)
tumor_mesh.export("pet_active_tumor_core.obj")
print(f"Generated PET Lesion Core: pet_active_tumor_core.obj ({len(verts_pet)} vertices)")
