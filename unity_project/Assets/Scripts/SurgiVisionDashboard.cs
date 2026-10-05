using UnityEngine;

// Dashboard data adapter. The prototype currently draws the compact overlay from its bootstrap;
// this component exposes the same live status for a future Canvas/UIToolkit dashboard.
public class SurgiVisionDashboard : MonoBehaviour
{
    public SurgiVisionPrototype prototype;
    public string SurgicalMode => prototype && prototype.planning ? "PLANNING" : "INTERACTIVE";
    public string HolographicMode => prototype && prototype.holographic ? "ON" : "OFF";
    public string SelectedTarget => prototype ? prototype.selectedTarget : "None";
    public string SafetyStatus => prototype && prototype.safety ? prototype.safety.State.ToString().ToUpperInvariant() : "INITIALIZING";
    public string HapticStatus => prototype && prototype.haptics ? prototype.haptics.State.ToString().ToUpperInvariant() : "INITIALIZING";
}
