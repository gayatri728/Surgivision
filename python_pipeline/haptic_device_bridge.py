import socket
import json
import time
import numpy as np
from margin_vector_engine import evaluate_tool_clearance

HAPTIC_OUT_PORT = 18945
BROADCAST_IP = "255.255.255.255"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Listen to incoming tool positions from tracker (port 18944)
in_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except AttributeError:
    pass
in_sock.bind(("", 18944))

print("=" * 68)
print(" SURGIVISION™ CLOSED-LOOP HAPTIC RESISTANCE BRIDGE ACTIVE")
print(f" Listening: UDP 18944 | Streaming Force Vectors to: UDP {HAPTIC_OUT_PORT}")
print("=" * 68)

try:
    while True:
        data, _ = in_sock.recvfrom(4096)
        packet = json.loads(data.decode("utf-8"))

        tool_pos = (
            packet["coords_lps_mm"]["x"],
            packet["coords_lps_mm"]["y"],
            packet["coords_lps_mm"]["z"]
        )

        # Precise KD-Tree boundary calculation
        metrics = evaluate_tool_clearance(tool_pos)
        force_mag = metrics["haptic_force_n"]
        approach_dir = np.array(metrics["approach_unit_vector"])

        # Resistive repulsive vector pushing backwards along approach direction
        resistive_vector = (-approach_dir * force_mag).round(3).tolist()

        haptic_packet = {
            "timestamp_ms": int(time.time() * 1000),
            "tool_position_lps": list(tool_pos),
            "closest_target_lps": metrics["closest_tumor_point_lps"],
            "margin_clearance_mm": metrics["minimum_margin_clearance_mm"],
            "repulsive_force_xyz_n": {
                "fx": resistive_vector[0],
                "fy": resistive_vector[1],
                "fz": resistive_vector[2]
            },
            "force_magnitude_n": force_mag,
            "safety_state": metrics["alarm_state"]
        }

        sock.sendto(json.dumps(haptic_packet).encode("utf-8"), (BROADCAST_IP, HAPTIC_OUT_PORT))

        print(f"[{metrics['alarm_state']:<26}] Margin: {metrics['minimum_margin_clearance_mm']:5.2f} mm | "
              f"Repulsive Force: ({resistive_vector[0]:5.2f}, {resistive_vector[1]:5.2f}, {resistive_vector[2]:5.2f}) N", end="\r")

except KeyboardInterrupt:
    print("\n Haptic feedback loop disengaged.")
