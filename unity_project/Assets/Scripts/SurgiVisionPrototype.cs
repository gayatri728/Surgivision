using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using System.IO;

public class SurgiVisionPrototype : MonoBehaviour
{
    [Header("3D Scene References")]
    public Transform liver;
    public Transform tool;
    public Transform[] zones;
    public SurgicalSafetySystem safety;
    public HapticSimulator haptics;
    public SurgiVisionAIPlaceholder ai;

    [Header("Navigation Telemetry")]
    public bool holographic;
    public bool planning;
    public string selectedTarget = "Target A";
    public Vector3 pathStart, pathEnd;
    public float targetSUV = 8.4f; // Standardized Uptake Value from 3D PET volume

    // Telemetry & Audit Counters
    private bool hasPath;
    private Camera cam;
    private Vector3 orbit = new Vector3(18, -25, 0);
    private float distance = 7f;
    private Material baseMat;
    private float procedureTimer = 0f;
    private int safetyViolations = 0;
    private bool wasInDanger = false;

    // UI Texture Cache
    private Texture2D panelBackground;
    private Texture2D progressBarTexture;

    void Start()
    {
        if (GraphicsSettings.currentRenderPipeline != null)
        {
            baseMat = GraphicsSettings.currentRenderPipeline.defaultMaterial;
        }
        else
        {
            baseMat = new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Sprites/Default"));
        }

        BuildDemo();

        cam = Camera.main;
        if (!cam)
        {
            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            cam = go.AddComponent<Camera>();
        }
        cam.transform.position = new Vector3(0, 1, -distance);
        cam.transform.LookAt(Vector3.zero);

        if (safety != null)
        {
            safety.tool = tool;
            safety.riskZones = zones;
        }

        // Initialize UI Textures
        panelBackground = MakeTexture(2, 2, new Color(0.04f, 0.07f, 0.11f, 0.92f));
        progressBarTexture = Texture2D.whiteTexture;
    }

    void BuildDemo()
    {
        // 1. Primary Organ Volume (Liver)
        liver = GameObject.CreatePrimitive(PrimitiveType.Sphere).transform;
        liver.name = "Anatomical Model (Liver)";
        liver.localScale = new Vector3(3.3f, 1.45f, 2.15f);
        ApplyColor(liver.gameObject, new Color(0.55f, 0.15f, 0.12f));

        // 2. Secondary Organ Structure
        var lobe = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lobe.name = "Secondary Lobe";
        lobe.transform.SetParent(liver);
        lobe.transform.localPosition = new Vector3(0.42f, 0.05f, 0);
        lobe.transform.localScale = new Vector3(0.76f, 0.83f, 0.95f);
        ApplyColor(lobe, new Color(0.55f, 0.15f, 0.12f));
        if (lobe.GetComponent<Collider>()) Destroy(lobe.GetComponent<Collider>());

        // 3. 3D PET Metabolic Risk Zones
        zones = new Transform[3];
        Vector3[] pos = { new Vector3(-0.72f, 0.38f, 0.35f), new Vector3(0.65f, -0.15f, 0.55f), new Vector3(0.15f, 0.45f, -0.72f) };
        for (int i = 0; i < zones.Length; i++)
        {
            var z = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            z.name = "PET Metabolic Risk Zone " + (i + 1);
            z.transform.position = pos[i];
            z.transform.localScale = Vector3.one * 0.75f;
            ApplyColor(z, new Color(1f, 0.35f, 0.0f));
            zones[i] = z.transform;
        }

        // 4. Virtual Surgical Tool
        var t = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        t.name = "Virtual Surgical Tool";
        t.transform.localScale = new Vector3(0.09f, 0.72f, 0.09f);
        t.transform.position = new Vector3(0, 0, -2.1f);
        t.transform.rotation = Quaternion.Euler(90, 0, 0);
        ApplyColor(t, new Color(0.0f, 0.85f, 1f));
        tool = t.transform;

        safety = gameObject.AddComponent<SurgicalSafetySystem>();
        haptics = gameObject.AddComponent<HapticSimulator>();
        ai = gameObject.AddComponent<SurgiVisionAIPlaceholder>();

        var lightGo = new GameObject("Key Light");
        lightGo.transform.rotation = Quaternion.Euler(35, -25, 0);
        lightGo.AddComponent<Light>().type = LightType.Directional;
    }

    void ApplyColor(GameObject go, Color col)
    {
        Renderer rend = go.GetComponent<Renderer>();
        if (!rend) return;

        Material instanceMat = new Material(baseMat);
        if (instanceMat.HasProperty("_BaseColor")) instanceMat.SetColor("_BaseColor", col);
        if (instanceMat.HasProperty("_Color")) instanceMat.SetColor("_Color", col);
        rend.material = instanceMat;
    }

    void Update()
    {
        procedureTimer += Time.deltaTime;

        var kb = Keyboard.current;
        var mouse = Mouse.current;

        // Orbit & Zoom controls
        if (mouse != null && mouse.leftButton.isPressed && !planning)
        {
            Vector2 delta = mouse.delta.ReadValue();
            orbit.y += delta.x * 0.3f;
            orbit.x -= delta.y * 0.3f;
        }

        if (mouse != null)
        {
            float scroll = mouse.scroll.ReadValue().y;
            distance = Mathf.Clamp(distance - scroll * 0.005f, 3.5f, 12f);
        }

        if (cam)
        {
            var rot = Quaternion.Euler(orbit);
            cam.transform.position = rot * new Vector3(0, 0, -distance);
            cam.transform.LookAt(Vector3.zero);
        }

        // WASD/QE Instrument Movement
        Vector3 move = Vector3.zero;
        if (kb != null)
        {
            if (kb.aKey.isPressed) move.x -= 1;
            if (kb.dKey.isPressed) move.x += 1;
            if (kb.wKey.isPressed) move.z += 1;
            if (kb.sKey.isPressed) move.z -= 1; // Fixed: move.z instead of move.s
            if (kb.eKey.isPressed) move.y += 1;
            if (kb.qKey.isPressed) move.y -= 1;

            if (kb.pKey.wasPressedThisFrame) { planning = !planning; hasPath = false; }
            if (kb.tKey.wasPressedThisFrame) { selectedTarget = selectedTarget == "Target A" ? "Target B" : "Target A"; }
            if (kb.hKey.wasPressedThisFrame) { holographic = !holographic; }
            if (kb.spaceKey.wasPressedThisFrame)
            {
                pathStart = tool.position;
                pathEnd = selectedTarget == "Target A" ? new Vector3(-0.9f, 0.25f, 0.7f) : new Vector3(1.05f, -0.2f, 0.45f);
                hasPath = true;
                if (safety != null) safety.EvaluatePath(pathStart, pathEnd);
            }
        }

        if (move.sqrMagnitude > 0 && tool != null)
            tool.position += move.normalized * Time.deltaTime * 1.5f;

        // Safety Violations Tracker
        if (safety != null)
        {
            if (safety.State == SafetyLevel.Danger && !wasInDanger)
            {
                safetyViolations++;
                wasInDanger = true;
            }
            else if (safety.State != SafetyLevel.Danger)
            {
                wasInDanger = false;
            }
        }
    }

    void OnGUI()
    {
        GUIStyle headerStyle = new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold, normal = { textColor = new Color(0.2f, 0.85f, 1f) } };
        GUIStyle subHeaderStyle = new GUIStyle(GUI.skin.label) { fontSize = 10, fontStyle = FontStyle.Italic, normal = { textColor = new Color(0.7f, 0.75f, 0.8f) } };
        GUIStyle sectionTitle = new GUIStyle(GUI.skin.label) { fontSize = 11, fontStyle = FontStyle.Bold, normal = { textColor = Color.white } };
        GUIStyle telemetryText = new GUIStyle(GUI.skin.label) { fontSize = 11, normal = { textColor = new Color(0.9f, 0.9f, 0.9f) } };

        // 1. LEFT PANEL: Clinical Navigation Telemetry
        GUI.DrawTexture(new Rect(16, 16, 380, 500), panelBackground);

        GUILayout.BeginArea(new Rect(28, 24, 356, 484));
        GUILayout.Label("SURGVISION  |  CLINICAL WORKSTATION", headerStyle);
        GUILayout.Label("Real-Time 3D PET Spatial Navigation", subHeaderStyle);
        GUILayout.Space(12);

        // System Mode
        GUILayout.Label("SYSTEM STATE", sectionTitle);
        GUILayout.Label($"Navigation Mode : {(planning ? "PRE-OP PLANNING" : "INTERACTIVE SURGERY")}", telemetryText);
        GUILayout.Label($"Rendering Engine : {(holographic ? "AR HOLOGRAPHIC SHADER" : "STANDARD URP")}", telemetryText);
        GUILayout.Label($"Target Focus    : {selectedTarget}", telemetryText);
        GUILayout.Space(10);

        // 3D PET Volumetric Data
        GUILayout.Label("3D PET VOLUMETRIC ANALYTICS", sectionTitle);
        GUILayout.Label($"Tumor Peak SUV  : {targetSUV:F1} g/mL (High Uptake Core)", telemetryText);
        GUILayout.Label($"Required Margin : 10.0 mm Clear Boundary", telemetryText);
        GUILayout.Space(10);

        // Live Tool Position & Trajectory
        if (tool != null)
        {
            GUILayout.Label("INSTRUMENT TELEMETRY", sectionTitle);
            GUILayout.Label($"Tool Tip Position : ({tool.position.x:F2}, {tool.position.y:F2}, {tool.position.z:F2})", telemetryText);
            float entryAngle = Vector3.Angle(tool.forward, Vector3.down);
            GUILayout.Label($"Entry Angle       : {entryAngle:F1}°", telemetryText);
        }
        GUILayout.Space(10);

        // Dynamic Proximity & Distance Bar
        if (safety != null)
        {
            GUILayout.Label("DYNAMIC SAFETY & PROXIMITY MONITOR", sectionTitle);

            Color statusColor = safety.State == SafetyLevel.Safe ? new Color(0.2f, 1f, 0.4f) :
                                safety.State == SafetyLevel.Caution ? new Color(1f, 0.85f, 0.1f) :
                                new Color(1f, 0.25f, 0.2f);

            GUI.color = statusColor;
            GUILayout.Label($"Safety Status : {safety.State.ToString().ToUpper()}", headerStyle);
            GUI.color = Color.white;

            float liveDist = safety.NearestBoundaryDistance;
            string distText = float.IsInfinity(liveDist) ? "CLEAR (> 2.00 m)" : $"{liveDist:F2} m to nearest risk zone";
            GUILayout.Label($"Margin Distance : {distText}", telemetryText);

            // Graphical Distance Bar
            float progress = Mathf.Clamp01(liveDist / 2.0f);
            Rect barRect = GUILayoutUtility.GetRect(340, 14, GUILayout.ExpandWidth(false));

            // Draw Progress Bar Background
            GUI.color = new Color(0.15f, 0.2f, 0.25f, 0.9f);
            GUI.DrawTexture(barRect, progressBarTexture);

            // Draw Active Proximity Fill
            GUI.color = statusColor;
            GUI.DrawTexture(new Rect(barRect.x, barRect.y, barRect.width * progress, barRect.height), progressBarTexture);
            GUI.color = Color.white;
        }
        GUILayout.Space(12);

        // Decision Support / AI Engine
        if (ai != null && safety != null)
        {
            GUILayout.Label("DECISION SUPPORT ENGINE", sectionTitle);
            GUILayout.Label($"AI Guidance : {ai.Assess(safety.State, hasPath && safety.PathIntersects)}", telemetryText);
        }
        GUILayout.EndArea();

        // 2. RIGHT PANEL: Procedural Session Audit
        GUI.DrawTexture(new Rect(Screen.width - 296, 16, 280, 220), panelBackground);

        GUILayout.BeginArea(new Rect(Screen.width - 284, 24, 256, 204));
        GUILayout.Label("PROCEDURAL AUDIT", headerStyle);
        GUILayout.Space(10);

        System.TimeSpan timerSpan = System.TimeSpan.FromSeconds(procedureTimer);
        GUILayout.Label($"Elapsed Time    : {timerSpan.Minutes:D2}:{timerSpan.Seconds:D2}", telemetryText);
        GUILayout.Label($"Risk Breaches   : {safetyViolations}", telemetryText);
        GUILayout.Space(14);

        if (GUILayout.Button("Export Telemetry Log (CSV)", GUILayout.Height(30)))
        {
            ExportTelemetryCSV();
        }
        GUILayout.EndArea();
    }

    Texture2D MakeTexture(int width, int height, Color col)
    {
        Color[] pix = new Color[width * height];
        for (int i = 0; i < pix.Length; i++) pix[i] = col;
        Texture2D result = new Texture2D(width, height);
        result.SetPixels(pix);
        result.Apply();
        return result;
    }

    void ExportTelemetryCSV()
    {
        string path = Application.dataPath + "/SurgiVision_Telemetry.csv";
        string log = $"Timestamp,Tool_X,Tool_Y,Tool_Z,Safety_State,Violations\n" +
                     $"{System.DateTime.Now:HH:mm:ss},{tool.position.x:F2},{tool.position.y:F2},{tool.position.z:F2},{safety.State},{safetyViolations}";
        File.WriteAllText(path, log);
        Debug.Log("Telemetry exported to: " + path);
    }

    void OnDrawGizmos()
    {
        if (hasPath)
        {
            Gizmos.color = (safety != null && safety.PathIntersects) ? Color.red : Color.green;
            Gizmos.DrawLine(pathStart, pathEnd);
            Gizmos.DrawSphere(pathEnd, 0.12f);
        }
    }
}
