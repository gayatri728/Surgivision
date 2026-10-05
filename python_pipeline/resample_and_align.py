import json
import numpy as np
import scipy.ndimage
from dicom_patient_loader import MedicalVolumeLoader

print("=" * 68)
print(" SURGIVISION™ ISOTROPIC RESAMPLING & AFFINE ALIGNMENT")
print(" Transforming Anisotropic PACS Grids to Isotropic 1.0mm Space")
print("=" * 68)

loader = MedicalVolumeLoader()
raw_hu_volume = loader.parse_dicom_series("sample_dicom_series")
orig_spacing = loader.voxel_spacing_mm  # (1.0, 1.0, 2.0) mm
target_spacing = (1.0, 1.0, 1.0)        # Isotropic 1.0 mm

print(f"Original Spacing: {orig_spacing} mm | Original Shape: {raw_hu_volume.shape}")

# Zoom factors per spatial axis
zoom_factors = [orig_spacing[i] / target_spacing[i] for i in range(3)]
print(f"Resampling Zoom Factors: {zoom_factors}")

# 3rd-order spline interpolation
resampled_volume = scipy.ndimage.zoom(raw_hu_volume, zoom_factors, order=3)
print(f" Resampled Isotropic Shape: {resampled_volume.shape}")

# Abdominal soft-tissue windowing (WL: 40, WW: 400 -> [-160, 240] HU)
window_min = -160.0
window_max = 240.0
windowed = np.clip(resampled_volume, window_min, window_max)
normalized_tensor = (windowed - window_min) / (window_max - window_min)

np.savez_compressed("aligned_isotropic_patient.npz", ct_volume=normalized_tensor)

alignment_meta = {
    "target_spacing_mm": list(target_spacing),
    "isotropic_shape": list(normalized_tensor.shape),
    "window_level_hu": 40.0,
    "window_width_hu": 400.0,
    "min_normalized_val": float(np.min(normalized_tensor)),
    "max_normalized_val": float(np.max(normalized_tensor))
}

with open("alignment_manifest.json", "w") as f:
    json.dump(alignment_meta, f, indent=4)

print(f" Normalized tensor exported: aligned_isotropic_patient.npz")
print(f" Spatial alignment manifest exported: alignment_manifest.json")
