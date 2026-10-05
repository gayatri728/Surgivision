using UnityEngine;

public class SurgicalSafetySystem : MonoBehaviour
{
    public Transform tool;
    public Transform[] riskZones;
    public float cautionDistance = 0.75f;
    public float dangerDistance = 0.28f;
    public SafetyLevel State { get; private set; } = SafetyLevel.Safe;
    public float NearestBoundaryDistance { get; private set; } = float.PositiveInfinity;
    public bool PathIntersects { get; private set; }

    void Update()
    {
        NearestBoundaryDistance = float.PositiveInfinity;
        if (tool != null && riskZones != null)
            foreach (var zone in riskZones)
                if (zone != null)
                {
                    var col = zone.GetComponent<Collider>();
                    float d = col ? Mathf.Max(0, Vector3.Distance(tool.position, zone.position) - col.bounds.extents.magnitude) : Vector3.Distance(tool.position, zone.position);
                    NearestBoundaryDistance = Mathf.Min(NearestBoundaryDistance, d);
                }
        State = NearestBoundaryDistance <= dangerDistance ? SafetyLevel.Danger :
                NearestBoundaryDistance <= cautionDistance ? SafetyLevel.Caution : SafetyLevel.Safe;
    }

    public void EvaluatePath(Vector3 start, Vector3 end)
    {
        PathIntersects = false;
        if (riskZones == null) return;
        foreach (var zone in riskZones)
            if (zone != null)
            {
                var col = zone.GetComponent<Collider>();
                float radius = col ? col.bounds.extents.magnitude : 0.5f;
                if (DistanceToSegment(zone.position, start, end) <= radius) { PathIntersects = true; break; }
            }
    }
    static float DistanceToSegment(Vector3 p, Vector3 a, Vector3 b)
    {
        Vector3 ab = b - a;
        float t = ab.sqrMagnitude < 0.0001f ? 0 : Mathf.Clamp01(Vector3.Dot(p-a, ab) / ab.sqrMagnitude);
        return Vector3.Distance(p, a + t * ab);
    }
}
