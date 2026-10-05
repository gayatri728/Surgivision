import os
import json
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

print("=" * 68)
print(" SURGIVISION™ CLINICAL PACS & RADIOLOGY INGESTION ENGINE")
print(" Standards: DICOM PS3.3 / NIfTI-1 Coordinate Transformation")
print("=" * 68)

class MedicalVolumeLoader:
    def __init__(self):
        self.voxel_spacing_mm = (1.0, 1.0, 1.0)
        self.patient_metadata = {}

    def parse_dicom_series(self, dicom_folder):
        """Loads and sorts an axial DICOM slice stack into a calibrated 3D volume."""
        if not os.path.exists(dicom_folder):
            raise FileNotFoundError(f"DICOM directory '{dicom_folder}' not found.")

        slice_files = [
            os.path.join(dicom_folder, f) 
            for f in os.listdir(dicom_folder) 
            if f.lower().endswith(".dcm")
        ]
        
        if not slice_files:
            raise ValueError(f"No .dcm files found in {dicom_folder}")

        print(f"Reading {len(slice_files)} DICOM slices...")
        slices = [pydicom.dcmread(f) for f in slice_files]
        
        # Sort slices along patient anatomical Z-axis
        slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))

        # Extract affine spatial resolution
        pixel_spacing = [float(x) for x in slices[0].PixelSpacing]
        slice_thickness = float(getattr(slices[0], "SliceThickness", 1.0))
        self.voxel_spacing_mm = (pixel_spacing[0], pixel_spacing[1], slice_thickness)

        # Build 3D array & convert raw pixel values to Hounsfield Units (HU)
        raw_volume = np.stack([s.pixel_array for s in slices], axis=-1).astype(np.float32)
        slope = float(getattr(slices[0], "RescaleSlope", 1.0))
        intercept = float(getattr(slices[0], "RescaleIntercept", 0.0))
        hu_volume = raw_volume * slope + intercept

        self.patient_metadata = {
            "patient_id": str(getattr(slices[0], "PatientID", "ANON_PATIENT")),
            "modality": str(getattr(slices[0], "Modality", "CT")),
            "dimensions": list(hu_volume.shape),
            "voxel_spacing_mm": list(self.voxel_spacing_mm)
        }

        print(f"DICOM Volume parsed: Shape {hu_volume.shape} | Spacing: {self.voxel_spacing_mm} mm")
        return hu_volume

    def generate_synthetic_dicom_case(self, output_folder="sample_dicom_series"):
        """Generates a fully-compliant DICOM test series with proper PS3.3 headers."""
        os.makedirs(output_folder, exist_ok=True)
        print(f"Synthesizing simulated clinical DICOM series in: {output_folder}/")
        
        study_uid = generate_uid()
        series_uid = generate_uid()

        for z_idx in range(32):
            # File Meta Information Header
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

            ds = Dataset()
            ds.file_meta = file_meta
            ds.is_little_endian = True
            ds.is_implicit_VR = False

            # Patient & Study Attributes
            ds.PatientName = "SURGICAL_PHANTOM_01"
            ds.PatientID = "SURGI_PAT_9901"
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = series_uid
            ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
            ds.Modality = "CT"

            # Image Spatial Geometry (LPS Frame)
            ds.PixelSpacing = [1.0, 1.0]
            ds.SliceThickness = 2.0
            ds.ImagePositionPatient = [0.0, 0.0, float(z_idx * 2.0)]
            ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"

            # Bit-Depth Configuration (Required for PixelData ambiguity resolution)
            ds.Rows, ds.Columns = 64, 64
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 0  # Unsigned 16-bit integer

            # Radiometric Calibration (HU = Pixel * RescaleSlope + RescaleIntercept)
            ds.RescaleSlope = 1.0
            ds.RescaleIntercept = -1024.0

            # Synthesize Tissue Densities: Parenchyma (~50 HU) + Bone Rim (~400 HU)
            yy, xx = np.ogrid[:64, :64]
            dist_from_center = np.sqrt((xx - 32)**2 + (yy - 32)**2)
            
            # Default background air: -1024 HU (raw value 0)
            slice_data = np.zeros((64, 64), dtype=np.uint16)
            
            # Soft tissue: ~50 HU (raw value 50 - (-1024) = 1074)
            slice_data[dist_from_center <= 24] = 1074
            # Bone perimeter: ~400 HU (raw value 400 - (-1024) = 1424)
            slice_data[(dist_from_center > 24) & (dist_from_center <= 27)] = 1424

            ds.PixelData = slice_data.tobytes()

            pydicom.filewriter.dcmwrite(
                os.path.join(output_folder, f"slice_{z_idx:03d}.dcm"),
                ds,
                write_like_original=False
            )

        print(f"Exported 32 DICOM slices to {output_folder}/")

if __name__ == "__main__":
    loader = MedicalVolumeLoader()
    sample_dir = "sample_dicom_series"
    loader.generate_synthetic_dicom_case(sample_dir)
    volume = loader.parse_dicom_series(sample_dir)
    
    with open("dicom_manifest.json", "w") as f:
        json.dump(loader.patient_metadata, f, indent=4)
        
    print(f"Clinical scan manifest exported: dicom_manifest.json")
