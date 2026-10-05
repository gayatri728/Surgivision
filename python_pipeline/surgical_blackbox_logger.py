import socket
import json
import time
import csv
import numpy as np

PORT = 18944

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except AttributeError:
    pass

# Bind to empty host string to listen for all broadcast packets
sock.bind(("", PORT))

print("=" * 65)
print(" SURGIVISION™ AUDIT & PROCEDURE FLIGHT RECORDER ACTIVE")
print(f" Listening for OpenIGTLink Broadcasts on Port {PORT}...")
print("=" * 65)

log_filename = f"session_telemetry_{int(time.time())}.csv"
csv_file = open(log_filename, mode="w", newline="")
writer = csv.writer(csv_file)
writer.writerow(["timestamp_ms", "pos_x_mm", "pos_y_mm", "pos_z_mm", "margin_mm", "force_n", "alarm_state"])

frame_count = 0
critical_events = 0
warning_events = 0
margins = []
forces = []
start_wall_time = time.time()

try:
    while True:
        data, _ = sock.recvfrom(4096)
        packet = json.loads(data.decode("utf-8"))

        ts = packet["timestamp_ms"]
        px = packet["coords_lps_mm"]["x"]
        py = packet["coords_lps_mm"]["y"]
        pz = packet["coords_lps_mm"]["z"]
        margin = packet["margin_clearance_mm"]
        force = packet["haptic_force_n"]
        state = packet["system_state"]

        writer.writerow([ts, px, py, pz, margin, force, state])
        csv_file.flush()

        frame_count += 1
        margins.append(margin)
        forces.append(force)

        if state == "CRITICAL_PERFORATION_RISK":
            critical_events += 1
        elif state == "WARNING_MARGIN_PROXIMITY":
            warning_events += 1

        elapsed = round(time.time() - start_wall_time, 1)
        print(f"[*] Recording Telemetry | Frames: {frame_count:05d} | T: {elapsed:5.1f}s | Margin: {margin:5.2f} mm | Violations: {critical_events}", end="\r")

except KeyboardInterrupt:
    csv_file.close()
    duration = time.time() - start_wall_time

    case_summary = {
        "case_id": f"CASE_{int(start_wall_time)}",
        "total_duration_sec": round(duration, 2),
        "total_frames_recorded": frame_count,
        "sampling_frequency_hz": round(frame_count / max(duration, 0.001), 1),
        "min_resection_margin_mm": round(float(np.min(margins)), 2) if margins else 0.0,
        "mean_resection_margin_mm": round(float(np.mean(margins)), 2) if margins else 0.0,
        "max_haptic_resistance_n": round(float(np.max(forces)), 2) if forces else 0.0,
        "warning_boundary_entries": warning_events,
        "critical_margin_breaches": critical_events,
        "surgical_safety_index": round(max(0.0, 100.0 - (critical_events * 0.8 + warning_events * 0.2)), 2),
        "telemetry_log_path": log_filename
    }

    with open("surgical_case_report.json", "w") as f:
        json.dump(case_summary, f, indent=4)

    print("\n" + "=" * 65)
    print(" SURGICAL PROCEDURE AUDIT REPORT COMPILED")
    print(f" • Log File: {log_filename}")
    print(f" • Duration: {case_summary['total_duration_sec']}s ({frame_count} frames)")
    print(f" • Minimum Margin Clearance: {case_summary['min_resection_margin_mm']} mm")
    print(f" • Critical Margin Breaches: {case_summary['critical_margin_breaches']}")
    print(f" • Safety Compliance Score: {case_summary['surgical_safety_index']}%")
    print("=" * 65)
