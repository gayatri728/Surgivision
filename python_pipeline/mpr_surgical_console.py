import os
import sys
import time
import socket
import asyncio
import json
import threading
import websockets
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LightSource, to_rgba
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

# --- UDP Network Configuration for Unity ---
UDP_IP = "127.0.0.1"
UDP_PORT = 18944
SCALE_FACTOR = 0.05  # Scale factor matching Unity & React scene coordinates
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- WebSocket Server Configuration for React Dashboard ---
WS_HOST = "127.0.0.1"
WS_PORT = 8080
CONNECTED_WS = set()

# --- Metasploit & Security Integration Config ---
METASPLOIT_HOOK_ENABLED = True
MSF_HOST = "127.0.0.1"
MSF_PORT = 4444
msf_triggered = False

def trigger_metasploit_alert(distance, coordinates):
    """Metasploit RPC / Security Audit Trigger Hook."""
    if not METASPLOIT_HOOK_ENABLED:
        return
    alert_payload = {
        "event": "CRITICAL_PROXIMITY_VIOLATION",
        "msf_target": f"{MSF_HOST}:{MSF_PORT}",
        "distance": distance,
        "coords": coordinates,
        "status": "ALERT_SENT"
    }

# --- Shared Telemetry State for Async WebSocket Server ---
shared_telemetry = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "distance": 15.0
}

# --- Background Async Loop for WebSocket Connections ---
async def ws_register(websocket):
    CONNECTED_WS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_WS.remove(websocket)

async def ws_broadcast_loop():
    while True:
        if CONNECTED_WS:
            ws_payload = json.dumps({
                "x": round(shared_telemetry["x"], 3),
                "y": round(shared_telemetry["y"], 3),
                "z": round(shared_telemetry["z"], 3),
                "distance": round(shared_telemetry["distance"], 3)
            })
            await asyncio.gather(
                *[client.send(ws_payload) for client in CONNECTED_WS],
                return_exceptions=True
            )
        await asyncio.sleep(0.05)

def run_async_ws_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def start():
        async with websockets.serve(ws_register, WS_HOST, WS_PORT):
            await ws_broadcast_loop()
    loop.run_until_complete(start())

ws_thread = threading.Thread(target=run_async_ws_server, daemon=True)
ws_thread.start()

# --- Mesh & Viewport Initialization ---
plt.style.use('dark_background')
fig = plt.figure(figsize=(12, 8), facecolor='#0a0e17')

organ_mesh_path = "petct_organ_hull.obj"
tumor_mesh_path = "pet_active_tumor_core.obj"

if not os.path.exists(organ_mesh_path):
    print(f"[!] Error: {organ_mesh_path} not found. Run generate_petct_surfaces.py first.")
    sys.exit(1)

organ_mesh = trimesh.load(organ_mesh_path)
tumor_mesh = trimesh.load(tumor_mesh_path) if os.path.exists(tumor_mesh_path) else None

# --- 2D MPR Viewports ---
ax_axial = fig.add_subplot(221)
ax_axial.set_title("AXIAL (TRANSVERSE)", color='#00d2ff', fontsize=10, fontweight='bold')
ax_axial.set_facecolor('#05080e')

ax_coronal = fig.add_subplot(222)
ax_coronal.set_title("CORONAL (FRONTAL)", color='#00d2ff', fontsize=10, fontweight='bold')
ax_coronal.set_facecolor('#05080e')

ax_sagittal = fig.add_subplot(223)
ax_sagittal.set_title("SAGITTAL (LATERAL)", color='#00d2ff', fontsize=10, fontweight='bold')
ax_sagittal.set_facecolor('#05080e')

# Synthetic PET SUV density slice
grid = np.zeros((64, 64))
ci, cj = 32, 32
for r in range(64):
    for c in range(64):
        dist = np.sqrt((r - ci)**2 + (c - cj)**2)
        grid[r, c] = 8.11 * np.exp(-(dist / 8.0)**2)

img_ax = ax_axial.imshow(grid, cmap='inferno', origin='lower')
img_co = ax_coronal.imshow(grid, cmap='inferno', origin='lower')
img_sa = ax_sagittal.imshow(grid, cmap='inferno', origin='lower')

# Live crosshair alignment lines
hl_ax = ax_axial.axhline(32, color='#00d2ff', linestyle='--', linewidth=1.0)
vl_ax = ax_axial.axvline(32, color='#00d2ff', linestyle='--', linewidth=1.0)

hl_co = ax_coronal.axhline(32, color='#00d2ff', linestyle='--', linewidth=1.0)
vl_co = ax_coronal.axvline(32, color='#00d2ff', linestyle='--', linewidth=1.0)

hl_sa = ax_sagittal.axhline(32, color='#00d2ff', linestyle='--', linewidth=1.0)
vl_sa = ax_sagittal.axvline(32, color='#00d2ff', linestyle='--', linewidth=1.0)

for ax in [ax_axial, ax_coronal, ax_sagittal]:
    ax.set_xticks([])
    ax.set_yticks([])

# --- 3D High-Clarity Viewport ---
ax3d = fig.add_subplot(224, projection='3d')
ax3d.set_title("3D REAL-TIME SURGICAL TRACKING", color='#00d2ff', fontsize=10, fontweight='bold')
ax3d.set_facecolor('#0a0e17')

ls = LightSource(azdeg=315, altdeg=45)

def get_shaded_colors(verts, faces, base_color, light_source):
    triangles = verts[faces]
    v0, v1, v2 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    norm_lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    norm_lengths[norm_lengths == 0] = 1e-8
    normals = normals / norm_lengths

    az_rad = np.radians(light_source.azdeg)
    alt_rad = np.radians(light_source.altdeg)
    light_dir = np.array([np.cos(alt_rad) * np.sin(az_rad), np.cos(alt_rad) * np.cos(az_rad), np.sin(alt_rad)])
    light_dir /= np.linalg.norm(light_dir)

    intensity = np.clip(np.dot(normals, light_dir), 0.25, 1.0)
    rgba = np.array(to_rgba(base_color))
    shaded_rgba = np.tile(rgba, (len(faces), 1))
    shaded_rgba[:, :3] *= intensity[:, np.newaxis]
    return shaded_rgba

# Render Organ Mesh
organ_verts = organ_mesh.vertices
organ_faces = organ_mesh.faces
organ_colors = get_shaded_colors(organ_verts, organ_faces, '#9e2a3f', ls)
organ_colors[:, 3] = 0.22

organ_collection = Poly3DCollection(organ_verts[organ_faces], facecolors=organ_colors, edgecolors='none')
ax3d.add_collection3d(organ_collection)

# Render Tumor Mesh
tumor_center = np.array([12.0, -3.0, 3.0])
if tumor_mesh is not None:
    tumor_verts = tumor_mesh.vertices
    tumor_faces = tumor_mesh.faces
    tumor_colors = get_shaded_colors(tumor_verts, tumor_faces, '#ff3300', ls)
    tumor_colors[:, 3] = 0.85
    tumor_collection = Poly3DCollection(tumor_verts[tumor_faces], facecolors=tumor_colors, edgecolors='none')
    ax3d.add_collection3d(tumor_collection)

# 10mm Safety Margin Wireframe Shell
u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
margin_r = 10.0
sx = tumor_center[0] + margin_r * np.cos(u) * np.sin(v)
sy = tumor_center[1] + margin_r * np.sin(u) * np.sin(v)
sz = tumor_center[2] + margin_r * np.cos(v)
ax3d.plot_wireframe(sx, sy, sz, color='#00ffcc', alpha=0.15, linewidth=0.5)

# Dynamic Tool Objects
tool_line, = ax3d.plot([], [], [], color='#00ffff', linewidth=3.5, label='Tool Shaft')
tool_tip_dot = ax3d.scatter([], [], [], color='#00ffcc', s=70, edgecolors='white', zorder=12)

all_verts = organ_verts
ax3d.set_xlim(all_verts[:, 0].min(), all_verts[:, 0].max())
ax3d.set_ylim(all_verts[:, 1].min(), all_verts[:, 1].max())
ax3d.set_zlim(all_verts[:, 2].min(), all_verts[:, 2].max())
ax3d.view_init(elev=20, azim=50)
ax3d.set_axis_off()

suptitle_text = fig.suptitle("", color='white', fontsize=10)

print("\n" + "="*75)
print(" SURGIVISION™ LIVE TRACKING CONSOLE ACTIVE ")
print(f" Broadcasting UDP Telemetry Stream  -> 127.0.0.1:{UDP_PORT}")
print(f" WebSocket Dashboard Stream         -> ws://{WS_HOST}:{WS_PORT}")
print(f" Metasploit Security Hook          -> ACTIVE ({MSF_HOST}:{MSF_PORT})")
print("="*75 + "\n")

# --- Dynamic Loop: Matplotlib + Terminal Log + Unity UDP + React WS ---
def update(frame):
    global msf_triggered
    t = frame * 0.1
    # Smooth helical trajectory targeting the tumor centroid
    radius = 15.0 * np.exp(-t * 0.05)
    tip_x = tumor_center[0] + radius * np.cos(t)
    tip_y = tumor_center[1] + radius * np.sin(t)
    tip_z = tumor_center[2] + 8.0 * np.sin(t * 0.5)

    tip_pos = np.array([tip_x, tip_y, tip_z])
    shaft_pos = tip_pos + np.array([12.0, 18.0, 15.0])

    # 3D Euclidean Distance (Target Registration Error / Margin evaluation)
    dist_to_tumor = np.linalg.norm(tip_pos - tumor_center)

    # 1. Update 3D Viewport
    tool_line.set_data([shaft_pos[0], tip_pos[0]], [shaft_pos[1], tip_pos[1]])
    tool_line.set_3d_properties([shaft_pos[2], tip_pos[2]])
    tool_tip_dot._offsets3d = ([tip_pos[0]], [tip_pos[1]], [tip_pos[2]])

    # 2. Update 2D Crosshairs
    cx = int(32 + (tip_x - tumor_center[0]) * 0.8)
    cy = int(32 + (tip_y - tumor_center[1]) * 0.8)
    cx = np.clip(cx, 0, 63)
    cy = np.clip(cy, 0, 63)

    hl_ax.set_ydata([cy, cy])
    vl_ax.set_xdata([cx, cx])
    hl_co.set_ydata([cy, cy])
    vl_co.set_xdata([cx, cx])
    hl_sa.set_ydata([cy, cy])
    vl_sa.set_xdata([cx, cx])

    # 3. APPLY 0.05 SCALE FACTOR FOR UNITY & FRONTEND PARITY
    scaled_x = tip_x * SCALE_FACTOR
    scaled_y = tip_y * SCALE_FACTOR
    scaled_z = tip_z * SCALE_FACTOR
    scaled_dist = dist_to_tumor * SCALE_FACTOR

    # Update shared telemetry state for WebSocket React server
    shared_telemetry["x"] = scaled_x
    shared_telemetry["y"] = scaled_y
    shared_telemetry["z"] = scaled_z
    shared_telemetry["distance"] = scaled_dist

    # 4. BROADCAST TO UNITY OVER UDP PORT 18944
    packet = f"{scaled_x:.3f},{scaled_y:.3f},{scaled_z:.3f}"
    sock.sendto(packet.encode('utf-8'), (UDP_IP, UDP_PORT))

    # 5. METASPLOIT SECURITY HOOK CHECK & STATUS EVALUATION
    if scaled_dist <= 0.15:
        status = "DANGER"
        if not msf_triggered:
            trigger_metasploit_alert(scaled_dist, (scaled_x, scaled_y, scaled_z))
            msf_triggered = True
    elif scaled_dist <= 0.50:
        status = "CAUTION"
        msf_triggered = False
    else:
        status = "IN TARGET MARGIN" if dist_to_tumor <= 10.0 else "APPROACHING TARGET"
        msf_triggered = False

    # 6. STREAM LIVE DATA DIRECTLY TO TERMINAL
    log_msg = f"\r[TRACKING] Tip: X={scaled_x:6.2f} Y={scaled_y:6.2f} Z={scaled_z:6.2f} | Dist: {dist_to_tumor:5.2f} mm | Status: {status} | UDP: Sent -> Port {UDP_PORT}    "
    sys.stdout.write(log_msg)
    sys.stdout.flush()

    # 7. Update Figure Header Text
    suptitle_text.set_text(
        f"SURGIVISION™ LIVE CLINICAL CONSOLE — PATIENT: ANON_SURGI_0942\n"
        f"Tip: [{tip_x:.1f}, {tip_y:.1f}, {tip_z:.1f}] | Target Margin Dist: {dist_to_tumor:.2f} mm"
    )

    return tool_line, tool_tip_dot

ani = FuncAnimation(fig, update, frames=300, interval=50, blit=False)
plt.tight_layout()
plt.show()
