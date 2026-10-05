import glob
import os
import pandas as pd
import matplotlib.pyplot as plt

# Locate the most recent session CSV
csv_files = glob.glob("session_telemetry_*.csv")
if not csv_files:
    print(" No session telemetry logs found.")
    exit(1)

latest_csv = max(csv_files, key=os.path.getctime)
print(f"[ Parsing Clinical Telemetry Session: {latest_csv}")

df = pd.read_csv(latest_csv)
df['time_sec'] = (df['timestamp_ms'] - df['timestamp_ms'].iloc[0]) / 1000.0

plt.style.use('dark_background')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, facecolor='#0B0F19')
fig.suptitle(f"SURGIVISION™ POST-OPERATIVE RESECTION METRICS\nSession Log: {latest_csv}", 
             fontsize=12, color='#94A3B8', fontweight='bold')

# Panel 1: Margin Clearance vs Safety Thresholds
ax1.set_facecolor('#111827')
ax1.plot(df['time_sec'], df['margin_mm'], color='#38BDF8', lw=1.5, label='Live Resection Margin (mm)')
ax1.axhline(10.0, color='#F59E0B', linestyle='--', lw=1.2, label='Recommended Margin Buffer (10mm)')
ax1.axhline(3.5, color='#EF4444', linestyle='--', lw=1.2, label='Critical Boundary Breach Threshold (3.5mm)')
ax1.fill_between(df['time_sec'], 0, 3.5, color='#EF4444', alpha=0.15)
ax1.set_ylabel("Margin Clearance (mm)", color='#F8FAFC', fontsize=10)
ax1.legend(loc='upper right', facecolor='#1E293B', edgecolor='none')
ax1.grid(True, linestyle=':', alpha=0.3)

# Panel 2: Dynamic Haptic Resistive Force (Newtons)
ax2.set_facecolor('#111827')
ax2.plot(df['time_sec'], df['force_n'], color='#A855F7', lw=1.5, label='Computed Tissue Feedback Force (N)')
ax2.set_ylabel("Haptic Force (N)", color='#F8FAFC', fontsize=10)
ax2.set_xlabel("Elapsed Time (Seconds)", color='#F8FAFC', fontsize=10)
ax2.legend(loc='upper right', facecolor='#1E293B', edgecolor='none')
ax2.grid(True, linestyle=':', alpha=0.3)

plt.tight_layout()
plt.savefig("surgical_analytics_report.png", dpi=300)
print(" Analytics plot saved: surgical_analytics_report.png")
plt.show()
