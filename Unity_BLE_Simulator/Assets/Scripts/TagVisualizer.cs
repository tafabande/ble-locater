using UnityEngine;
using System;
using System.Text;
using System.Threading;
using System.Net.WebSockets;

[Serializable]
public class PosData {
    public float x;
    public float y;
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
    public string websocketUrl = "ws://127.0.0.1:8000/ws";
    public float scaleFactor = 1.0f; 
    public float smoothingSpeed = 5.0f;

    private ClientWebSocket ws;
    private Vector3 targetPosition;
    private float nextX;
    private float nextZ;
    private bool newPosAvailable = false;

    async void Start()
    {
        targetPosition = transform.position;
        ws = new ClientWebSocket();
        try {
            await ws.ConnectAsync(new Uri(websocketUrl), CancellationToken.None);
            Debug.Log("[Ghost Tag] Connected to Backend!");
            ReceiveLoop();
        } catch(Exception e) {
            Debug.LogError("[Ghost Tag] Connection failed: " + e.Message);
        }
    }

    void Update()
    {
        if (newPosAvailable) {
            targetPosition = new Vector3(nextX, transform.position.y, nextZ);
            newPosAvailable = false;
        }
        transform.position = Vector3.Lerp(transform.position, targetPosition, Time.deltaTime * smoothingSpeed);
    }

    async void ReceiveLoop()
    {
        var buffer = new byte[8192]; 
        while (ws.State == WebSocketState.Open)
        {
            try {
                var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Close) {
                    await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                } else {
                    string json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    string safeJson = json.Replace("\"event\":", "\"eventName\":");
                    WSEvent evt = JsonUtility.FromJson<WSEvent>(safeJson); 
                    if (evt != null && evt.eventName == "position_update" && evt.data != null && evt.data.position != null) {
                        nextX = evt.data.position.x * scaleFactor;
                        nextZ = evt.data.position.y * scaleFactor;
                        newPosAvailable = true;
                    }
                }
            } catch (Exception) { break; }
        }
    }

    private void OnDestroy() {
        if (ws != null) ws.Dispose();
    }
}
