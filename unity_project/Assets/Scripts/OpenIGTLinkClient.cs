using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

[System.Serializable]
public class LPSCoords
{
    public float x;
    public float y;
    public float z;
}

[System.Serializable]
public class SurgicalTelemetryPacket
{
    public long timestamp_ms;
    public string frame_id;
    public LPSCoords coords_lps_mm;
    public float margin_clearance_mm;
    public float haptic_force_n;
    public string system_state;
}

public class OpenIGTLinkClient : MonoBehaviour
{
    [Header("Network Configuration")]
    [SerializeField] private int listenPort = 18944;

    [Header("Surgical Scene Bindings")]
    [SerializeField] private Transform toolTipIndicator;
    [SerializeField] private Renderer tumorRenderer;
    [SerializeField] private TMPro.TextMeshProUGUI hudTelemetryText;

    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isRunning = false;

    // Thread-safe buffer
    private SurgicalTelemetryPacket latestPacket;
    private readonly object packetLock = new object();

    void Start()
    {
        InitializeUDPReceiver();
    }

    private void InitializeUDPReceiver()
    {
        try
        {
            udpClient = new UdpClient();
            udpClient.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            udpClient.Client.Bind(new IPEndPoint(IPAddress.Any, listenPort));

            isRunning = true;
            receiveThread = new Thread(new ThreadStart(ReceiveDataPool))
            {
                IsBackground = true
            };
            receiveThread.Start();
            Debug.Log($"[SurgiVision] Listening for UDP telemetry on port {listenPort}...");
        }
        catch (Exception ex)
        {
            Debug.LogError($"[SurgiVision] Network initialization failed: {ex.Message}");
        }
    }

    private void ReceiveDataPool()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
        while (isRunning)
        {
            try
            {
                byte[] rawBytes = udpClient.Receive(ref remoteEndPoint);
                string jsonPayload = Encoding.UTF8.GetString(rawBytes);
                SurgicalTelemetryPacket parsed = JsonUtility.FromJson<SurgicalTelemetryPacket>(jsonPayload);

                lock (packetLock)
                {
                    latestPacket = parsed;
                }
            }
            catch (SocketException)
            {
                // Socket closed or interrupted
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[SurgiVision] Telemetry frame parse error: {ex.Message}");
            }
        }
    }

    void Update()
    {
        SurgicalTelemetryPacket packet = null;
        lock (packetLock)
        {
            if (latestPacket != null)
            {
                packet = latestPacket;
            }
        }

        if (packet != null)
        {
            ApplyTelemetry(packet);
        }
    }

    private void ApplyTelemetry(SurgicalTelemetryPacket packet)
    {
        // Clinical LPS to Unity Left-Handed Coordinate Conversion:
        // LPS: X = Left, Y = Posterior, Z = Superior
        // Unity: X = Right, Y = Up, Z = Forward
        // Conversion: Unity.x = -LPS.x, Unity.y = LPS.z, Unity.z = LPS.y
        Vector3 unitySpacePosition = new Vector3(
            -packet.coords_lps_mm.x * 0.001f, // Scaled mm to Unity meters
             packet.coords_lps_mm.z * 0.001f,
             packet.coords_lps_mm.y * 0.001f
        );

        if (toolTipIndicator != null)
        {
            toolTipIndicator.localPosition = unitySpacePosition;
        }

        // Margin safety state handling
        Color alertColor = Color.green;
        if (packet.system_state == "CRITICAL_PERFORATION_RISK")
        {
            alertColor = Color.red;
        }
        else if (packet.system_state == "WARNING_MARGIN_PROXIMITY")
        {
            alertColor = Color.yellow;
        }

        if (tumorRenderer != null)
        {
            tumorRenderer.material.SetColor("_EmissionColor", alertColor * (packet.system_state == "CRITICAL_PERFORATION_RISK" ? 2.5f : 1.0f));
        }

        if (hudTelemetryText != null)
        {
            hudTelemetryText.text = $"MARGIN: {packet.margin_clearance_mm:F2} mm\n" +
                                   $"FORCE: {packet.haptic_force_n:F1} N\n" +
                                   $"STATE: {packet.system_state}";
            hudTelemetryText.color = alertColor;
        }
    }

    void OnDestroy()
    {
        isRunning = false;
        if (udpClient != null)
        {
            udpClient.Close();
        }
        if (receiveThread != null && receiveThread.IsAlive)
        {
            receiveThread.Abort();
        }
    }
}
