# SURGIVISION: Real-Time 3D PET Spatial Navigation & Surgical Telemetry System

SURGIVISION is an interactive 3D surgical guidance workstation and research stack built with **Unity (URP)** and a **Python-based volumetric PET/CT reconstruction pipeline**. 

Unlike standard passive PET/CT slice viewers, SURGIVISION converts functional metabolic imaging into an **active 3D safety coordinate system**, featuring dynamic proximity tracking, vector entry analytics, real-time safety boundary monitoring, and procedural audit logging.

---

##  Key Features & Innovations

* **Volumetric PET Reconstruction:** Converts 2D DICOM slice stacks into aligned isotropic voxel arrays and extracts 3D surface meshes using Marching Cubes and Standardized Uptake Value ($SUV$) thresholding.
* **Active Safety Coordinate System:** Dynamic distance evaluation between surgical instruments and high-uptake metabolic risk zones (`SAFE` $\rightarrow$ `CAUTION` $\rightarrow$ `DANGER`).
* **In-Engine Clinical Workstation HUD:** Dark-themed clinical overlay displaying Cartesian tool tip coordinates $(x, y, z)$, entry vector angles, $SUV_{\text{max}}$ analytics, and color-shifting proximity meters.
* **Procedural Audit & Session Logging:** Automatically tracks active procedure duration, records boundary breaches, and exports structured CSV telemetry logs for post-operative evaluation.
* **Research Analytics Suite:** Automated generation of safety breach distributions, trajectory angular stability charts, and clearance margin reports.

---

##  System Architecture & Repository Structure

```text
SURGIVISION_GitHub/
├── python_pipeline/                # Backend Data Engine & Safety Math
│   ├── dicom_patient_loader.py     # Parses raw DICOM image series
│   ├── resample_and_align.py       # Isotropic voxel resampling
│   ├── monai_petct_segmenter.py    # Deep learning organ/tumor segmentation
│   ├── generate_petct_surfaces.py # Marching Cubes surface mesh extraction (.obj)
│   ├── margin_vector_engine.py    # Dynamic proximity & clearance math
│   ├── igtl_surgical_tracker.py   # OpenIGTLink tracking protocol driver
│   ├── haptic_device_bridge.py    # Force feedback & haptic integration
│   ├── surgical_blackbox_logger.py# Procedural session logger
│   ├── plot_surgical_analytics.py # Automated clinical performance plotting
│   ├── aligned_isotropic_patient.npz # Resampled volume dataset
│   ├── requirements.txt            # Python dependencies
│   └── surgical_analytics_report.png # Sample evaluation output
├── unity_project/                  # Unity URP Runtime Interactive Engine
│   ├── Assets/
│   │   ├── Scripts/
│   │   │   ├── SurgiVisionPrototype.cs # Primary HUD & Navigation controller
│   │   │   └── OpenIGTLinkClient.cs    # Network tracking receiver
│   │   ├── petct_organ_hull.obj       # Reconstructed organ mesh
│   │   └── pet_active_tumor_core.obj  # High-uptake PET tumor core mesh
│   └── ProjectSettings/
├── .gitignore                      # Unity cache & local log exclusions
└── README.md                       # Project documentation
