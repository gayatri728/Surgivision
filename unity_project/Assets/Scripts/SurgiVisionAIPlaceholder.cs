using UnityEngine;

public class SurgiVisionAIPlaceholder : MonoBehaviour
{
    public string Assess(SafetyLevel toolState, bool pathIntersects)
    {
        if (pathIntersects || toolState == SafetyLevel.Danger) return "HIGH — revise path / increase clearance";
        if (toolState == SafetyLevel.Caution) return "MODERATE — review proximity";
        return "LOW — no simulated boundary conflict";
    }
    public string Notice => "Research prototype heuristic; not a validated AI model.";
}
