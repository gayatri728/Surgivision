import json
import trimesh
import numpy as np
from scipy.spatial import cKDTree

print("=" * 68)
print(" SURGIVISION™ MINIMUM DISTANCE & SURFACE VECTOR ENGINE")
print(" Spatial Precision: SciPy KD-Tree Nearest-Surface Projection")
print("=" * 68)

# 1. Load clinical surface meshes
tumor_mesh = trimesh.load("pet_active_tumor_core.obj")
organ_mesh = trimesh.load("petct_organ_hull.obj")

# 2. Build high-speed KD-Trees over mesh vertex clouds
tumor_tree = cKDTree(tumor_mesh.vertices)
organ_tree = cKDTree(organ_mesh.vertices)

print(f"Spatial trees indexed: Tumor vertices={len(tumor_mesh.vertices)}, Organ vertices={len(organ_mesh.vertices)}")

def evaluate_tool_clearance(tool_pos_lps):
    tool_pt = np.array(tool_pos_lps)

    # Minimum Euclidean distance to closest vertex on the surface
    tumor_dist, tumor_v_idx = tumor_tree.query(tool_pt)
    organ_dist, _ = organ_tree.query(tool_pt)

    closest_tumor_pt = tumor_mesh.vertices[tumor_v_idx]

    # Vector pointing from tool tip to nearest lesion point
    approach_vector = closest_tumor_pt - tool_pt
    norm = np.linalg.norm(approach_vector)
    unit_direction = (approach_vector / norm).tolist() if norm > 1e-6 else [0.0, 0.0, 0.0]

    critical_threshold_mm = 3.5
    warning_threshold_mm = 10.0

    if tumor_dist < critical_threshold_mm:
        state = "CRITICAL_PERFORATION_RISK"
        force_n = round(min(18.0, 4.0 + (critical_threshold_mm - tumor_dist) * 4.5), 2)
    elif tumor_dist < warning_threshold_mm:
        state = "WARNING_MARGIN_PROXIMITY"
        force_n = round((warning_threshold_mm - tumor_dist) * 0.7, 2)
    else:
        state = "NOMINAL"
        force_n = 0.0

    return {
        "tool_pos_lps": list(tool_pos_lps),
        "closest_tumor_point_lps": closest_tumor_pt.tolist(),
        "minimum_margin_clearance_mm": round(float(tumor_dist), 3),
        "organ_capsule_distance_mm": round(float(organ_dist), 3),
        "approach_unit_vector": [round(v, 4) for v in unit_direction],
        "haptic_force_n": force_n,
        "alarm_state": state
    }

if __name__ == "__main__":
    test_coordinates = [
        (18.0, 10.0, 15.0),
        (6.0, 0.0, 5.0),
        (2.0, -1.0, 2.0)
    ]

    results = []
    print("\n Evaluating Spatial Trajectory Waypoints:")
    for pt in test_coordinates:
        metrics = evaluate_tool_clearance(pt)
        results.append(metrics)
        print(f" -> Probe: {pt} | Margin: {metrics['minimum_margin_clearance_mm']:6.2f} mm | State: {metrics['alarm_state']:<26} | Force: {metrics['haptic_force_n']:4.1f} N")

    with open("margin_vector_benchmarks.json", "w") as f:
        json.dump(results, f, indent=4)

    print(f"\n Vector benchmark audit exported: margin_vector_benchmarks.json")
