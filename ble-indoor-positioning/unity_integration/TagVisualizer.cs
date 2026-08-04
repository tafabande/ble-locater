using UnityEngine;
using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;

// Data structures for parsing the Python JSON payload using JsonUtility
[Serializable]
public class PosData {
    public float x;
    public float y;
    public float uncertainty;
    public float gdop;
}

[Serializable]
public class UpdateData {
    public PosData position;
}

[Serializable]
public class WSEvent {
    public string eventName;
    public UpdateData data;
}

public class TagVisualizer : MonoBehaviour
{
    [Header("Connection Settings")]
    public string websocketUrl = "ws://127.0.0.1:8000/ws";
    
    [Header("Coordinate Mapping")]
    [Tooltip("Scales the Python coordinates (meters) to Unity world units.")]
    public float scaleFactor = 1.0f; 
    [Tooltip("How fast the tag smoothly interpolates to the new position.")]
    public float smoothingSpeed = 5.0f;

    private ClientWebSocket ws;
    private Vector3 targetPosition;
    private bool positionUpdated = false;

    // We can't use Unity APIs from a background thread, so we queue the updates
    private float nextX;
    private float nextZ;
    private bool newPosAvailable = false;

    async void Start()
    {
        targetPosition = transform.position;
        ws = new ClientWebSocket();
        
        try {
            await ws.ConnectAsync(new Uri(websocketUrl), CancellationToken.None);
            Debug.Log("[BLE Visualizer] Connected to Backend WebSocket!");
            ReceiveLoop();
        } catch(Exception e) {
            Debug.LogError("[BLE Visualizer] Connection failed: " + e.Message);
        }
    }

    void Update()
    {
        // Thread-safe transfer of position data to the main thread
        if (newPosAvailable) {
            // Unity uses X and Z for the horizontal floor plane, Y is vertical (up)
            targetPosition = new Vector3(nextX, transform.position.y, nextZ);
            newPosAvailable = false;
        }

        // Smoothly interpolate current position towards the latest target position
        transform.position = Vector3.Lerp(transform.position, targetPosition, Time.deltaTime * smoothingSpeed);
    }

    async void ReceiveLoop()
    {
        var buffer = new byte[8192]; // 8KB buffer for the JSON payload
        while (ws.State == WebSocketState.Open)
        {
            try
            {
                var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                    Debug.Log("[BLE Visualizer] WebSocket closed cleanly.");
                }
                else
                {
                    string json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    
                    // Hack to workaround JsonUtility not allowing fields named "event" (C# keyword)
                    // We replace the "event" key with "eventName" before parsing.
                    string safeJson = json.Replace("\"event\":", "\"eventName\":");
                    
                    WSEvent evt = JsonUtility.FromJson<WSEvent>(safeJson); 
                    if (evt != null && evt.eventName == "position_update" && evt.data != null && evt.data.position != null) {
                        
                        // Pass data safely to the main Unity thread
                        nextX = evt.data.position.x * scaleFactor;
                        nextZ = evt.data.position.y * scaleFactor;
                        newPosAvailable = true;
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning("[BLE Visualizer] Read error (connection may have dropped): " + e.Message);
                break;
            }
        }
    }

    private async void OnDestroy() {
        if (ws != null && ws.State == WebSocketState.Open) {
            try {
                await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
            } catch (Exception) {
                // Ignore exceptions on destroy
            }
        }
        if (ws != null) {
            ws.Dispose();
        }
    }
}
