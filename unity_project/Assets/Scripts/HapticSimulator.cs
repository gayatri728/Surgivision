using UnityEngine;

public enum SafetyLevel { Safe, Caution, Danger }

public class HapticSimulator : MonoBehaviour
{
    public SafetyLevel State { get; private set; } = SafetyLevel.Safe;
    public float SimulatedIntensity { get; private set; }
    public string DeviceAdapterStatus => "Visual simulation (hardware adapter ready)";

    public void SetState(SafetyLevel state, float normalizedIntensity)
    {
        State = state;
        SimulatedIntensity = Mathf.Clamp01(normalizedIntensity);
        // Future device adapter seam: forward normalizedIntensity to a supported haptic SDK here.
    }
}
