using UnityEngine;
using System;
using System.Text;
using System.Threading;
using System.Net.WebSockets;
using System.Globalization;

public class TagVisualizer : MonoBehaviour
{
    public string websocketUrl = "ws://127.0.0.1:8000/ws";
    public float scaleFactor = 1.0f; 
    public float smoothingSpeed = 12.0f;
    public TextMesh hudText;

    public string predictedRoom = "Calculating...";
    public float predictedX = 2.5f;
    public float predictedZ = 7.5f;
    public float trackingError = 0f;
    public string currentZone = "Calculating...";

    private ClientWebSocket ws;
    private Vector3 targetPosition;
    private float nextX = 2.5f;
    private float nextZ = 7.5f;
    private bool newPosAvailable = false;
    private Transform trueTagTransform;

    async void Start()
    {
        GameObject trueTag = GameObject.Find("True_Tag (Drag Me)");
        if (trueTag != null) {
            trueTagTransform = trueTag.transform;
            transform.position = trueTagTransform.position;
            targetPosition = trueTagTransform.position;
            predictedX = transform.position.x;
            predictedZ = transform.position.z;
        }

        ws = new ClientWebSocket();
        try {
            await ws.ConnectAsync(new Uri(websocketUrl), CancellationToken.None);
            Debug.Log("[Ghost Tag] Connected to ML Backend WebSocket!");
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
        predictedX = transform.position.x;
        predictedZ = transform.position.z;

        if (trueTagTransform != null) {
            trackingError = Vector3.Distance(new Vector3(transform.position.x, 0, transform.position.z), 
                                             new Vector3(trueTagTransform.position.x, 0, trueTagTransform.position.z));
        }

        if (hudText != null && Camera.main != null) {
            hudText.text = string.Format("\ud83c\udfaf PREDICTED GHOST\nPos: ({0:F2}m, {1:F2}m)", 
                transform.position.x, transform.position.z);
            hudText.transform.rotation = Quaternion.LookRotation(hudText.transform.position - Camera.main.transform.position);
        }
    }

    async void ReceiveLoop()
    {
        var buffer = new byte[8192]; 
        while (ws != null && ws.State == WebSocketState.Open)
        {
            try {
                var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Close) {
                    await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                } else {
                    string json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    
                    try {
                        int xIdx = json.IndexOf(""x":");
                        int yIdx = json.IndexOf(""y":");
                        if (xIdx != -1 && yIdx != -1) {
                            int xEnd = json.IndexOf(",", xIdx);
                            int yEnd = json.IndexOf(",", yIdx);
                            if (xEnd != -1 && yEnd != -1) {
                                string xStr = json.Substring(xIdx + 4, xEnd - (xIdx + 4)).Trim();
                                string yStr = json.Substring(yIdx + 4, yEnd - (yIdx + 4)).Trim();
                                
                                nextX = float.Parse(xStr, CultureInfo.InvariantCulture) * scaleFactor;
                                nextZ = float.Parse(yStr, CultureInfo.InvariantCulture) * scaleFactor;

                                int roomIdx = json.IndexOf(""room":");
                                if (roomIdx != -1) {
                                    int q1 = json.IndexOf(""", roomIdx + 7);
                                    int q2 = json.IndexOf(""", q1 + 1);
                                    if (q1 != -1 && q2 != -1) {
                                        predictedRoom = json.Substring(q1 + 1, q2 - (q1 + 1));
                                    }
                                }

                                int zoneIdx = json.IndexOf(""zone":");
                                if (zoneIdx != -1) {
                                    int q1 = json.IndexOf(""", zoneIdx + 7);
                                    int q2 = json.IndexOf(""", q1 + 1);
                                    if (q1 != -1 && q2 != -1) {
                                        currentZone = json.Substring(q1 + 1, q2 - (q1 + 1));
                                    }
                                }

                                newPosAvailable = true;
                            }
                        }
                    } catch (Exception parseEx) {
                        Debug.LogWarning("[Ghost Tag Direct Parse Exception] " + parseEx.Message);
                    }
                }
            } catch (Exception) { break; }
        }
    }

    private void OnDestroy() {
        if (ws != null) ws.Dispose();
    }
}
