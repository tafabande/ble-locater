import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {path}")

def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Unity_BLE_Simulator")
    scripts_dir = os.path.join(base_dir, "Assets", "Scripts")
    editor_dir = os.path.join(base_dir, "Assets", "Editor")

    print(f"Generating High-Detail 4-Room Hospital Floorplan in: {base_dir}")

    # 1. BLESimulator.cs
    ble_sim_code = """using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Text;

[System.Serializable]
public class RawPacket {
    public long timestamp;
    public string anchor;
    public string mac;
    public int rssi;
    public string name;
    public float true_x;
    public float true_y;
}

public class BLESimulator : MonoBehaviour
{
    [Header("Network Settings")]
    public string batchUrl = "http://127.0.0.1:8000/api/observation/batch";
    public string macAddress = "52:06:26:03:01:DA";
    public float updateRateHz = 10f;

    [Header("Calibrated Dataset RSSI Parameters")]
    public float txPowerAt1m = -77.8f; 
    public float pathLossExponentClear = 2.4f;
    public float pathLossExponentObstacle = 3.6f;
    public float noiseStdDev = 0.5f; 

    [Header("HUD Display")]
    public TextMesh hudText;

    private Transform[] anchors;
    private string[] anchorIds = { 
        "ANCHOR_01", "ANCHOR_02", "ANCHOR_03", 
        "ANCHOR_04", "ANCHOR_05", "ANCHOR_06",
        "ANCHOR_07", "ANCHOR_08", "ANCHOR_09",
        "ANCHOR_10", "ANCHOR_11", "ANCHOR_12"
    };
    private LineRenderer[] lineRenderers;

    void Start()
    {
        anchors = new Transform[12];
        lineRenderers = new LineRenderer[12];

        for (int i = 0; i < 12; i++)
        {
            GameObject anchorObj = GameObject.Find(anchorIds[i]);
            if (anchorObj != null) anchors[i] = anchorObj.transform;

            GameObject lineObj = new GameObject("RayBeam_" + anchorIds[i]);
            lineObj.transform.SetParent(transform);
            LineRenderer lr = lineObj.AddComponent<LineRenderer>();
            lr.startWidth = 0.03f;
            lr.endWidth = 0.03f;
            lr.material = new Material(Shader.Find("Sprites/Default"));
            lineRenderers[i] = lr;
        }

        StartCoroutine(SimulateAndSendBatch());
    }

    void Update()
    {
        if (hudText != null && Camera.main != null)
        {
            hudText.text = string.Format("📱 PATIENT TAG (TAG_01)\\nPos: ({0:F2}m, {1:F2}m)", 
                transform.position.x, transform.position.z);
            hudText.transform.rotation = Quaternion.LookRotation(hudText.transform.position - Camera.main.transform.position);
        }
    }

    IEnumerator SimulateAndSendBatch()
    {
        while (true)
        {
            long timestamp = System.DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            List<string> packetJsons = new List<string>();

            for (int i = 0; i < 12; i++)
            {
                if (anchors[i] == null) continue;

                Vector3 toAnchor = anchors[i].position - transform.position;
                float distance = toAnchor.magnitude;
                if (distance < 0.1f) distance = 0.1f;

                float currentPathLoss = pathLossExponentClear;
                bool isObstructed = false;

                if (Physics.Raycast(transform.position, toAnchor.normalized, out RaycastHit hit, distance))
                {
                    if (hit.collider.CompareTag("Obstacle"))
                    {
                        currentPathLoss = pathLossExponentObstacle;
                        isObstructed = true;
                    }
                }

                if (lineRenderers[i] != null)
                {
                    lineRenderers[i].SetPosition(0, transform.position + Vector3.up * 0.2f);
                    lineRenderers[i].SetPosition(1, anchors[i].position + Vector3.up * 0.2f);
                    Color rayColor = isObstructed ? new Color(1f, 0.2f, 0.2f, 0.4f) : new Color(0.2f, 1f, 0.4f, 0.6f);
                    lineRenderers[i].startColor = rayColor;
                    lineRenderers[i].endColor = rayColor;
                }

                float rssiFloat = txPowerAt1m - 10f * currentPathLoss * Mathf.Log10(distance);
                
                float u1 = 1.0f - Random.value;
                float u2 = 1.0f - Random.value;
                float randStdNormal = Mathf.Sqrt(-2.0f * Mathf.Log(u1)) * Mathf.Sin(2.0f * Mathf.PI * u2);
                float noise = noiseStdDev * randStdNormal;

                int finalRssi = Mathf.RoundToInt(Mathf.Clamp(rssiFloat + noise, -110f, -30f));

                RawPacket packet = new RawPacket {
                    timestamp = timestamp,
                    anchor = anchorIds[i],
                    mac = macAddress,
                    rssi = finalRssi,
                    name = "SIMULATED_TAG",
                    true_x = transform.position.x,
                    true_y = transform.position.z
                };

                packetJsons.Add(JsonUtility.ToJson(packet));
            }

            if (packetJsons.Count > 0)
            {
                string batchJson = "[" + string.Join(",", packetJsons.ToArray()) + "]";
                StartCoroutine(PostRequest(batchUrl, batchJson));
            }

            yield return new WaitForSeconds(1f / updateRateHz);
        }
    }

    IEnumerator PostRequest(string url, string json)
    {
        var request = new UnityWebRequest(url, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(json);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();
    }
}
"""

    # 2. PlayerController.cs
    player_ctrl_code = """using UnityEngine;

public class PlayerController : MonoBehaviour
{
    public float moveSpeed = 3.5f;
    public float turnSpeed = 120f;
    private Plane dragPlane;

    void Start()
    {
        dragPlane = new Plane(Vector3.up, transform.position);
    }

    void OnMouseDown()
    {
        dragPlane = new Plane(Vector3.up, transform.position);
    }

    void OnMouseDrag()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        if (dragPlane.Raycast(ray, out float enter))
        {
            Vector3 hitPoint = ray.GetPoint(enter);
            hitPoint.y = 0.4f; 
            hitPoint.x = Mathf.Clamp(hitPoint.x, 0.2f, 9.8f);
            hitPoint.z = Mathf.Clamp(hitPoint.z, 0.2f, 9.8f);
            transform.position = hitPoint;
        }
    }

    void Update()
    {
        float turnInput = 0f;
        if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) turnInput = -1f;
        if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) turnInput = 1f;

        transform.Rotate(Vector3.up, turnInput * turnSpeed * Time.deltaTime);

        float moveInput = 0f;
        if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) moveInput = 1f;
        if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) moveInput = -1f;

        if (Mathf.Abs(moveInput) > 0.01f)
        {
            Vector3 moveDir = transform.forward * moveInput * moveSpeed * Time.deltaTime;
            Vector3 targetPos = transform.position + moveDir;

            targetPos.x = Mathf.Clamp(targetPos.x, 0.2f, 9.8f);
            targetPos.z = Mathf.Clamp(targetPos.z, 0.2f, 9.8f);
            targetPos.y = 0.4f;

            if (!Physics.CheckSphere(targetPos, 0.35f, LayerMask.GetMask("Default"), QueryTriggerInteraction.Ignore))
            {
                transform.position = targetPos;
            }
        }
    }
}
"""

    # 3. CameraController.cs
    camera_ctrl_code = """using UnityEngine;

public enum CameraViewMode
{
    Overview = 0,
    FirstPerson = 1,
    ThirdPerson = 2
}

public class CameraController : MonoBehaviour
{
    public CameraViewMode currentMode = CameraViewMode.Overview;
    public Transform targetPlayer;

    public float panSpeed = 12f;
    public float zoomSpeed = 10f;
    public float rotateSpeed = 60f;
    public float minZoom = 2f;
    public float maxZoom = 20f;

    private Vector3 lastMousePos;
    private Vector3 overviewCenter = new Vector3(5.0f, 0, 5.0f);

    void Start()
    {
        GameObject trueTag = GameObject.Find("True_Tag (Drag Me)");
        if (trueTag != null) targetPlayer = trueTag.transform;
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.C))
        {
            CycleCameraMode();
        }

        if (targetPlayer == null)
        {
            GameObject trueTag = GameObject.Find("True_Tag (Drag Me)");
            if (trueTag != null) targetPlayer = trueTag.transform;
            return;
        }

        switch (currentMode)
        {
            case CameraViewMode.Overview:
                UpdateOverview();
                break;
            case CameraViewMode.FirstPerson:
                UpdateFirstPerson();
                break;
            case CameraViewMode.ThirdPerson:
                UpdateThirdPerson();
                break;
        }
    }

    public void CycleCameraMode()
    {
        currentMode = (CameraViewMode)(((int)currentMode + 1) % 3);
        Debug.Log("[Camera] Switched View Mode to: " + currentMode);
    }

    void UpdateOverview()
    {
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (Mathf.Abs(scroll) > 0.001f)
        {
            Camera.main.orthographicSize = Mathf.Clamp(Camera.main.orthographicSize - scroll * zoomSpeed, minZoom, maxZoom);
            transform.position += transform.forward * scroll * zoomSpeed;
        }

        if (Input.GetMouseButtonDown(1) || Input.GetMouseButtonDown(2))
        {
            lastMousePos = Input.mousePosition;
        }

        if (Input.GetMouseButton(1) || Input.GetMouseButton(2))
        {
            Vector3 delta = Input.mousePosition - lastMousePos;
            Vector3 move = (-transform.right * delta.x - transform.up * delta.y) * panSpeed * 0.002f;
            transform.position += move;
            lastMousePos = Input.mousePosition;
        }

        if (Input.GetKey(KeyCode.Q))
        {
            transform.RotateAround(overviewCenter, Vector3.up, rotateSpeed * Time.deltaTime);
        }
        if (Input.GetKey(KeyCode.E))
        {
            transform.RotateAround(overviewCenter, Vector3.up, -rotateSpeed * Time.deltaTime);
        }
    }

    void UpdateFirstPerson()
    {
        Vector3 eyePos = targetPlayer.position + Vector3.up * 1.2f;
        transform.position = eyePos;
        transform.rotation = Quaternion.Slerp(transform.rotation, targetPlayer.rotation, Time.deltaTime * 12f);
    }

    void UpdateThirdPerson()
    {
        Vector3 desiredPos = targetPlayer.position - targetPlayer.forward * 2.5f + Vector3.up * 1.8f;
        transform.position = Vector3.Lerp(transform.position, desiredPos, Time.deltaTime * 10f);
        transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(targetPlayer.position + Vector3.up * 0.8f - transform.position), Time.deltaTime * 10f);
    }
}
"""

    # 4. HumanWalker.cs
    human_walker_code = """using UnityEngine;
using System.Collections;

public class HumanWalker : MonoBehaviour
{
    public Vector3[] waypoints;
    public float walkSpeed = 1.3f;
    public float pauseTimeAtWaypoint = 2.0f;
    public TextMesh labelText;

    private int currentWaypointIndex = 0;

    void Start()
    {
        if (waypoints == null || waypoints.Length == 0)
        {
            waypoints = new Vector3[] {
                new Vector3(2.5f, 0.9f, 2.5f), // Room C
                new Vector3(2.5f, 0.9f, 7.5f), // Room A
                new Vector3(7.5f, 0.9f, 7.5f), // Room B
                new Vector3(7.5f, 0.9f, 2.5f)  // Room D
            };
        }
        StartCoroutine(PatrolRoutine());
    }

    IEnumerator PatrolRoutine()
    {
        while (true)
        {
            Vector3 targetPos = waypoints[currentWaypointIndex];
            targetPos.y = 0.9f;

            while (Vector3.Distance(new Vector3(transform.position.x, 0, transform.position.z), 
                                     new Vector3(targetPos.x, 0, targetPos.z)) > 0.2f)
            {
                Vector3 dir = (targetPos - transform.position).normalized;
                
                if (Physics.Raycast(transform.position, dir, out RaycastHit hit, 0.8f))
                {
                    if (!hit.collider.isTrigger && !hit.collider.name.Contains("Door"))
                    {
                        dir = Vector3.Cross(hit.normal, Vector3.up).normalized;
                    }
                }

                transform.position += dir * walkSpeed * Time.deltaTime;
                transform.position = new Vector3(Mathf.Clamp(transform.position.x, 0.3f, 9.7f), 0.9f, Mathf.Clamp(transform.position.z, 0.3f, 9.7f));
                
                if (dir != Vector3.zero)
                {
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), Time.deltaTime * 6f);
                }
                yield return null;
            }

            yield return new WaitForSeconds(pauseTimeAtWaypoint);
            currentWaypointIndex = (currentWaypointIndex + 1) % waypoints.Length;
        }
    }

    void Update()
    {
        if (labelText != null && Camera.main != null)
        {
            labelText.transform.rotation = Quaternion.LookRotation(labelText.transform.position - Camera.main.transform.position);
        }
    }
}
"""

    # 5. DoorController.cs
    door_ctrl_code = """using UnityEngine;

public class DoorController : MonoBehaviour
{
    public float openDistance = 2.4f;
    public float openSpeed = 5.0f;
    public Vector3 slideOffset = Vector3.zero;

    private Vector3 closedPos;
    private Vector3 openPos;
    private Collider doorCollider;

    void Start()
    {
        closedPos = transform.position;
        doorCollider = GetComponent<Collider>();

        if (transform.localScale.x > transform.localScale.z)
        {
            slideOffset = new Vector3(-1.4f, 0, 0);
        }
        else
        {
            slideOffset = new Vector3(0, 0, 1.4f);
        }

        openPos = closedPos + slideOffset;
    }

    void Update()
    {
        bool shouldOpen = false;

        Collider[] hitColliders = Physics.OverlapSphere(transform.position, openDistance);
        foreach (var hit in hitColliders)
        {
            if (hit.gameObject != gameObject && (
                hit.name.Contains("True_Tag") || 
                hit.name.Contains("Ghost_Tag") || 
                hit.name.Contains("Dr_") || 
                hit.name.Contains("Nurse_") || 
                hit.name.Contains("Visitor_") || 
                hit.GetComponent<HumanWalker>() != null
            ))
            {
                shouldOpen = true;
                break;
            }
        }

        Vector3 targetPos = shouldOpen ? openPos : closedPos;
        transform.position = Vector3.Lerp(transform.position, targetPos, Time.deltaTime * openSpeed);

        if (doorCollider != null)
        {
            float distToOpen = Vector3.Distance(transform.position, openPos);
            doorCollider.isTrigger = (distToOpen < 0.35f);
        }
    }
}
"""

    # 6. TagVisualizer.cs (BULLETPROOF DIRECT PARSER - Bypasses JsonUtility Dictionary Bug)
    tag_vis_code = """using UnityEngine;
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
            hudText.text = string.Format("🎯 PREDICTED GHOST\\nPos: ({0:F2}m, {1:F2}m)", 
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
                    
                    // Bulletproof Extraction: Bypasses JsonUtility Dictionary Limitations
                    try {
                        int xIdx = json.IndexOf("\\"x\\":");
                        int yIdx = json.IndexOf("\\"y\\":");
                        if (xIdx != -1 && yIdx != -1) {
                            int xEnd = json.IndexOf(",", xIdx);
                            int yEnd = json.IndexOf(",", yIdx);
                            if (xEnd != -1 && yEnd != -1) {
                                string xStr = json.Substring(xIdx + 4, xEnd - (xIdx + 4)).Trim();
                                string yStr = json.Substring(yIdx + 4, yEnd - (yIdx + 4)).Trim();
                                
                                nextX = float.Parse(xStr, CultureInfo.InvariantCulture) * scaleFactor;
                                nextZ = float.Parse(yStr, CultureInfo.InvariantCulture) * scaleFactor;

                                int roomIdx = json.IndexOf("\\"room\\":");
                                if (roomIdx != -1) {
                                    int q1 = json.IndexOf("\\"", roomIdx + 7);
                                    int q2 = json.IndexOf("\\"", q1 + 1);
                                    if (q1 != -1 && q2 != -1) {
                                        predictedRoom = json.Substring(q1 + 1, q2 - (q1 + 1));
                                    }
                                }

                                int zoneIdx = json.IndexOf("\\"zone\\":");
                                if (zoneIdx != -1) {
                                    int q1 = json.IndexOf("\\"", zoneIdx + 7);
                                    int q2 = json.IndexOf("\\"", q1 + 1);
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
"""

    # 7. HUDTableUI.cs
    hud_table_code = """using UnityEngine;

public class HUDTableUI : MonoBehaviour
{
    private Transform trueTag;
    private TagVisualizer ghostTag;
    private CameraController camCtrl;
    private GUIStyle headerStyle;
    private GUIStyle valueStyle;
    private GUIStyle buttonStyle;
    private Texture2D bgTexture;

    void Start()
    {
        GameObject trueObj = GameObject.Find("True_Tag (Drag Me)");
        if (trueObj != null) trueTag = trueObj.transform;

        GameObject ghostObj = GameObject.Find("Ghost_Tag (Predicted)");
        if (ghostObj != null) ghostTag = ghostObj.GetComponent<TagVisualizer>();

        if (Camera.main != null) camCtrl = Camera.main.GetComponent<CameraController>();

        bgTexture = new Texture2D(1, 1);
        bgTexture.SetPixel(0, 0, new Color(0.08f, 0.09f, 0.12f, 0.92f));
        bgTexture.Apply();
    }

    private string ResolveRoomName(float x, float z)
    {
        if (x < 5.0f && z >= 5.0f) return "Room A (ICU Bedroom 1)";
        if (x >= 5.0f && z >= 5.0f) return "Room B (Patient Bedroom 2)";
        if (x < 5.0f && z < 5.0f) return "Room C (Medical Station)";
        return "Room D (Emergency Ward)";
    }

    void OnGUI()
    {
        if (headerStyle == null)
        {
            headerStyle = new GUIStyle(GUI.skin.label);
            headerStyle.fontSize = 11;
            headerStyle.fontStyle = FontStyle.Bold;
            headerStyle.normal.textColor = new Color(0.5f, 0.8f, 1.0f);
            headerStyle.alignment = TextAnchor.MiddleCenter;

            valueStyle = new GUIStyle(GUI.skin.label);
            valueStyle.fontSize = 12;
            valueStyle.fontStyle = FontStyle.Bold;
            valueStyle.normal.textColor = Color.white;
            valueStyle.alignment = TextAnchor.MiddleCenter;

            buttonStyle = new GUIStyle(GUI.skin.button);
            buttonStyle.fontSize = 11;
            buttonStyle.fontStyle = FontStyle.Bold;
            buttonStyle.normal.textColor = Color.yellow;
        }

        float width = Screen.width;
        float height = 75f;
        float top = Screen.height - height;

        GUI.DrawTexture(new Rect(0, top, width, height), bgTexture);

        float trueX = trueTag != null ? trueTag.position.x : 0f;
        float trueZ = trueTag != null ? trueTag.position.z : 0f;
        string actualRoom = ResolveRoomName(trueX, trueZ);

        string ghostRoom = ghostTag != null ? ghostTag.predictedRoom : "Calculating...";
        float ghostX = ghostTag != null ? ghostTag.predictedX : 0f;
        float ghostZ = ghostTag != null ? ghostTag.predictedZ : 0f;
        float error = ghostTag != null ? ghostTag.trackingError : 0f;
        string zone = ghostTag != null ? ghostTag.currentZone : "Unknown";

        float colWidth = width / 5f;

        // Column 1: Actual Room & Coordinates
        GUI.Label(new Rect(0 * colWidth, top + 8, colWidth, 20), "🏢 ACTUAL ROOM & LOCATION", headerStyle);
        GUI.Label(new Rect(0 * colWidth, top + 32, colWidth, 30), string.Format("{0}\\n({1:F2}m, {2:F2}m)", actualRoom, trueX, trueZ), valueStyle);

        // Column 2: Ghost Room & Coordinates
        GUI.Label(new Rect(1 * colWidth, top + 8, colWidth, 20), "🎯 PREDICTED GHOST LOCATION", headerStyle);
        GUI.Label(new Rect(1 * colWidth, top + 32, colWidth, 30), string.Format("{0}\\n({1:F2}m, {2:F2}m)", ghostRoom, ghostX, ghostZ), valueStyle);

        // Column 3: Real-Time MAE Error Rate
        GUI.Label(new Rect(2 * colWidth, top + 8, colWidth, 20), "📏 TRACKING ERROR RATE", headerStyle);
        GUI.Label(new Rect(2 * colWidth, top + 34, colWidth, 30), string.Format("{0:F2} METERS", error), valueStyle);

        // Column 4: Predicted ML Zone
        GUI.Label(new Rect(3 * colWidth, top + 8, colWidth, 20), "🏷️ PREDICTED ML ZONE", headerStyle);
        GUI.Label(new Rect(3 * colWidth, top + 34, colWidth, 30), zone, valueStyle);

        // Column 5: Camera Mode & Switcher Button
        string modeStr = camCtrl != null ? camCtrl.currentMode.ToString().ToUpper() : "OVERVIEW";
        GUI.Label(new Rect(4 * colWidth, top + 6, colWidth, 18), "📷 CAMERA VIEW: " + modeStr, headerStyle);
        if (GUI.Button(new Rect(4 * colWidth + 20, top + 28, colWidth - 40, 32), "SWITCH VIEW (C)", buttonStyle))
        {
            if (camCtrl != null) camCtrl.CycleCameraMode();
        }
    }
}
"""

    # 8. DraggableObstacle.cs
    draggable_code = """using UnityEngine;

public class DraggableObstacle : MonoBehaviour
{
    private Plane dragPlane;

    void OnMouseDown()
    {
        dragPlane = new Plane(Vector3.up, transform.position);
    }

    void OnMouseDrag()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        if (dragPlane.Raycast(ray, out float enter))
        {
            Vector3 hitPoint = ray.GetPoint(enter);
            hitPoint.y = transform.position.y;
            transform.position = hitPoint;
        }
    }
}
"""

    # 9. SceneBuilder.cs
    scene_builder_code = """#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class SceneBuilder : EditorWindow
{
    [MenuItem("BLE Demo/Generate High-Detail Zimbabwean Hospital")]
    public static void GenerateScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // 1. Room Floor (10m x 10m Hospital Complex)
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Hospital_Floor_Complex";
        floor.transform.position = new Vector3(5.0f, 0, 5.0f);
        floor.transform.localScale = new Vector3(1.0f, 1, 1.0f);
        Material floorMat = new Material(Shader.Find("Standard"));
        floorMat.color = new Color(0.85f, 0.88f, 0.90f);
        floorMat.SetFloat("_Glossiness", 0.4f);
        floor.GetComponent<Renderer>().sharedMaterial = floorMat;

        // Tag Manager setup
        SerializedObject tagManager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        SerializedProperty tagsProp = tagManager.FindProperty("tags");
        bool found = false;
        for (int i = 0; i < tagsProp.arraySize; i++) {
            if (tagsProp.GetArrayElementAtIndex(i).stringValue.Equals("Obstacle")) { found = true; break; }
        }
        if (!found) {
            tagsProp.InsertArrayElementAtIndex(0);
            tagsProp.GetArrayElementAtIndex(0).stringValue = "Obstacle";
            tagManager.ApplyModifiedProperties();
        }

        // Palette & Materials
        Material wallMat = new Material(Shader.Find("Standard"));
        wallMat.color = new Color(0.92f, 0.95f, 0.96f);

        Material frameMat = new Material(Shader.Find("Standard"));
        frameMat.color = new Color(0.2f, 0.25f, 0.3f);

        Material windowGlassMat = new Material(Shader.Find("Standard"));
        windowGlassMat.SetFloat("_Mode", 3);
        windowGlassMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        windowGlassMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        windowGlassMat.SetInt("_ZWrite", 0);
        windowGlassMat.EnableKeyword("_ALPHABLEND_ON");
        windowGlassMat.renderQueue = 3000;
        windowGlassMat.color = new Color(0.6f, 0.85f, 0.95f, 0.35f);

        Material doorWoodMat = new Material(Shader.Find("Standard"));
        doorWoodMat.color = new Color(0.55f, 0.35f, 0.2f);

        Material bedFrameMat = new Material(Shader.Find("Standard"));
        bedFrameMat.color = new Color(0.3f, 0.35f, 0.4f);

        Material mattressMat = new Material(Shader.Find("Standard"));
        mattressMat.color = new Color(0.2f, 0.5f, 0.8f);

        Material blanketMat = new Material(Shader.Find("Standard"));
        blanketMat.color = new Color(0.1f, 0.6f, 0.4f);

        Material woodMat = new Material(Shader.Find("Standard"));
        woodMat.color = new Color(0.6f, 0.4f, 0.25f);

        // Zimbabwean Melanin Skin Tone Palettes
        Material zimDoctorSkin = new Material(Shader.Find("Standard"));
        zimDoctorSkin.color = new Color(0.22f, 0.14f, 0.08f); 

        Material zimNurseSkin = new Material(Shader.Find("Standard"));
        zimNurseSkin.color = new Color(0.25f, 0.16f, 0.10f); 

        Material zimVisitorSkin = new Material(Shader.Find("Standard"));
        zimVisitorSkin.color = new Color(0.20f, 0.12f, 0.07f); 

        Material doctorCoatMat = new Material(Shader.Find("Standard"));
        doctorCoatMat.color = new Color(0.95f, 0.95f, 0.98f);

        Material nurseMat = new Material(Shader.Find("Standard"));
        nurseMat.color = new Color(0.1f, 0.6f, 0.7f);

        Material visitorMat = new Material(Shader.Find("Standard"));
        visitorMat.color = new Color(0.85f, 0.35f, 0.2f); 

        Material sunflowerYellow = new Material(Shader.Find("Standard"));
        sunflowerYellow.color = new Color(1.0f, 0.85f, 0.0f);
        sunflowerYellow.EnableKeyword("_EMISSION");
        sunflowerYellow.SetColor("_EmissionColor", new Color(0.3f, 0.25f, 0.0f));

        Material sunflowerBrown = new Material(Shader.Find("Standard"));
        sunflowerBrown.color = new Color(0.3f, 0.18f, 0.05f);

        Material stemGreen = new Material(Shader.Find("Standard"));
        stemGreen.color = new Color(0.15f, 0.6f, 0.15f);

        Material potMat = new Material(Shader.Find("Standard"));
        potMat.color = new Color(0.7f, 0.35f, 0.2f);

        // 2. Outer Enclosing Boundary Walls + Glass Windows
        BuildWall("Wall_North", new Vector3(5.0f, 1.25f, 10.0f), new Vector3(10.2f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_South", new Vector3(5.0f, 1.25f, 0.0f), new Vector3(10.2f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_West", new Vector3(0.0f, 1.25f, 5.0f), new Vector3(0.2f, 2.5f, 10.2f), wallMat);
        BuildWall("Wall_East", new Vector3(10.0f, 1.25f, 5.0f), new Vector3(0.2f, 2.5f, 10.2f), wallMat);

        BuildWindow("Window_North_RoomA", new Vector3(2.5f, 1.4f, 9.95f), new Vector3(1.6f, 1.0f, 0.08f), windowGlassMat, frameMat);
        BuildWindow("Window_North_RoomB", new Vector3(7.5f, 1.4f, 9.95f), new Vector3(1.6f, 1.0f, 0.08f), windowGlassMat, frameMat);

        // 3. Interior Isolation Dividing Walls with Animated Automatic Doors
        BuildWall("Wall_Div_H_Left", new Vector3(1.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_Div_H_Right", new Vector3(8.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildDoor("SlidingDoor_RoomA_to_C", new Vector3(4.0f, 1.1f, 5.0f), doorWoodMat);

        BuildWall("Wall_Div_V_Bottom", new Vector3(5.0f, 1.25f, 1.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildWall("Wall_Div_V_Top", new Vector3(5.0f, 1.25f, 8.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildDoor("SlidingDoor_RoomA_to_B", new Vector3(5.0f, 1.1f, 6.0f), doorWoodMat);

        // 4. 4-Room Furniture & Patient Setup
        BuildBedWithPatient("Bed_RoomA", new Vector3(1.4f, 0, 7.5f), bedFrameMat, mattressMat, blanketMat, zimDoctorSkin, "Patient Rufaro (ICU Bed A)");
        CreateSunflowerPot(new Vector3(0.5f, 0, 9.5f), "Sunflower_RoomA", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildBedWithPatient("Bed_RoomB", new Vector3(6.4f, 0, 7.5f), bedFrameMat, mattressMat, blanketMat, zimNurseSkin, "Patient Nyasha (Bed B)");
        CreateSunflowerPot(new Vector3(9.5f, 0, 9.5f), "Sunflower_RoomB", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        GameObject deskC = GameObject.CreatePrimitive(PrimitiveType.Cube);
        deskC.name = "Nurse_Desk_RoomC";
        deskC.tag = "Obstacle";
        deskC.transform.position = new Vector3(2.5f, 0.4f, 2.5f);
        deskC.transform.localScale = new Vector3(1.8f, 0.8f, 0.8f);
        deskC.GetComponent<Renderer>().sharedMaterial = woodMat;
        deskC.AddComponent<DraggableObstacle>();
        CreateSunflowerPot(new Vector3(0.5f, 0, 0.5f), "Sunflower_RoomC", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildBedWithPatient("Emergency_Bed_RoomD", new Vector3(8.5f, 0, 2.5f), bedFrameMat, mattressMat, blanketMat, zimVisitorSkin, "Emergency Triage Bed");
        CreateSunflowerPot(new Vector3(9.5f, 0, 0.5f), "Sunflower_RoomD", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        // 5. 12 Beacon Anchors (3 per room)
        Vector3[] anchorPositions = { 
            new Vector3(0.2f, 0, 5.2f), new Vector3(4.8f, 0, 5.2f), new Vector3(2.5f, 0, 9.8f), // Room A
            new Vector3(5.2f, 0, 5.2f), new Vector3(9.8f, 0, 5.2f), new Vector3(7.5f, 0, 9.8f), // Room B
            new Vector3(0.2f, 0, 0.2f), new Vector3(4.8f, 0, 0.2f), new Vector3(2.5f, 0, 4.8f), // Room C
            new Vector3(5.2f, 0, 0.2f), new Vector3(9.8f, 0, 0.2f), new Vector3(7.5f, 0, 4.8f)  // Room D
        };
        string[] anchorNames = { 
            "ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04", "ANCHOR_05", "ANCHOR_06",
            "ANCHOR_07", "ANCHOR_08", "ANCHOR_09", "ANCHOR_10", "ANCHOR_11", "ANCHOR_12"
        };

        Material pylonMat = new Material(Shader.Find("Standard"));
        pylonMat.color = new Color(0.2f, 0.25f, 0.3f);
        
        Material emitterMat = new Material(Shader.Find("Standard"));
        emitterMat.color = new Color(0f, 0.9f, 0.5f);
        emitterMat.EnableKeyword("_EMISSION");
        emitterMat.SetColor("_EmissionColor", new Color(0f, 0.8f, 0.4f));

        for (int i = 0; i < 12; i++) {
            GameObject anchorRoot = new GameObject(anchorNames[i]);
            anchorRoot.transform.position = anchorPositions[i];

            GameObject pylon = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            pylon.transform.SetParent(anchorRoot.transform);
            pylon.transform.localPosition = new Vector3(0, 0.75f, 0);
            pylon.transform.localScale = new Vector3(0.3f, 0.75f, 0.3f);
            pylon.GetComponent<Renderer>().sharedMaterial = pylonMat;

            GameObject emitter = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            emitter.transform.SetParent(anchorRoot.transform);
            emitter.transform.localPosition = new Vector3(0, 1.6f, 0);
            emitter.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
            emitter.GetComponent<Renderer>().sharedMaterial = emitterMat;

            GameObject labelObj = new GameObject("Label");
            labelObj.transform.SetParent(anchorRoot.transform);
            labelObj.transform.localPosition = new Vector3(0, 2.2f, 0);
            TextMesh tm = labelObj.AddComponent<TextMesh>();
            tm.text = anchorNames[i] + string.Format("\\n({0:F1}, {1:F1})", anchorPositions[i].x, anchorPositions[i].z);
            tm.fontSize = 22;
            tm.characterSize = 0.07f;
            tm.color = Color.cyan;
            tm.alignment = TextAlignment.Center;
            tm.anchor = TextAnchor.MiddleCenter;
        }

        // 6. Detailed Zimbabwean Healthcare Staff & Visitor Walking Entities
        CreateWalkingHuman("Dr_Tendai", new Vector3(2.5f, 0.9f, 2.5f), doctorCoatMat, zimDoctorSkin, new Vector3[] {
            new Vector3(2.5f, 0.9f, 2.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 2.5f)
        }, "👨‍⚕️ Dr. Tendai (Consultant)");

        CreateWalkingHuman("Nurse_Chipo", new Vector3(7.5f, 0.9f, 2.5f), nurseMat, zimNurseSkin, new Vector3[] {
            new Vector3(7.5f, 0.9f, 2.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 2.5f)
        }, "👩‍⚕️ Nurse Chipo (Ward Lead)");

        CreateWalkingHuman("Visitor_Farai", new Vector3(6.5f, 0.9f, 6.5f), visitorMat, zimVisitorSkin, new Vector3[] {
            new Vector3(6.5f, 0.9f, 6.5f), new Vector3(3.0f, 0.9f, 3.0f), new Vector3(8.0f, 0.9f, 3.0f), new Vector3(6.5f, 0.9f, 6.5f)
        }, "🏃 Visitor Farai");

        // 7. Patient Smartphone Tag Device (True Tag)
        GameObject trueTag = new GameObject("True_Tag (Drag Me)");
        trueTag.transform.position = new Vector3(2.5f, 0.4f, 7.5f);
        BoxCollider tagCol = trueTag.AddComponent<BoxCollider>();
        tagCol.size = new Vector3(0.6f, 0.4f, 0.8f);

        GameObject phoneBody = GameObject.CreatePrimitive(PrimitiveType.Cube);
        phoneBody.name = "PhoneBody";
        phoneBody.transform.SetParent(trueTag.transform);
        phoneBody.transform.localPosition = Vector3.zero;
        phoneBody.transform.localScale = new Vector3(0.35f, 0.06f, 0.65f);
        Material bodyMat = new Material(Shader.Find("Standard"));
        bodyMat.color = new Color(0.1f, 0.1f, 0.12f);
        phoneBody.GetComponent<Renderer>().sharedMaterial = bodyMat;

        GameObject phoneScreen = GameObject.CreatePrimitive(PrimitiveType.Quad);
        phoneScreen.name = "PhoneScreen";
        phoneScreen.transform.SetParent(trueTag.transform);
        phoneScreen.transform.localPosition = new Vector3(0, 0.035f, 0);
        phoneScreen.transform.localRotation = Quaternion.Euler(90f, 0, 0);
        phoneScreen.transform.localScale = new Vector3(0.3f, 0.58f, 1f);
        Material phoneScreenMat = new Material(Shader.Find("Standard"));
        phoneScreenMat.color = new Color(0.9f, 0.1f, 0.1f);
        phoneScreenMat.EnableKeyword("_EMISSION");
        phoneScreenMat.SetColor("_EmissionColor", new Color(0.8f, 0.1f, 0.1f));
        phoneScreen.GetComponent<Renderer>().sharedMaterial = phoneScreenMat;

        GameObject trueHudObj = new GameObject("HUD");
        trueHudObj.transform.SetParent(trueTag.transform);
        trueHudObj.transform.localPosition = new Vector3(0, 1.2f, 0);
        TextMesh trueTm = trueHudObj.AddComponent<TextMesh>();
        trueTm.fontSize = 24;
        trueTm.characterSize = 0.07f;
        trueTm.color = new Color(1f, 0.4f, 0.4f);
        trueTm.alignment = TextAlignment.Center;
        trueTm.anchor = TextAnchor.MiddleCenter;

        trueTag.AddComponent<PlayerController>();
        BLESimulator sim = trueTag.AddComponent<BLESimulator>();
        sim.hudText = trueTm;

        // 8. Predicted Holographic Tag Device (Ghost Tag)
        GameObject ghostTag = new GameObject("Ghost_Tag (Predicted)");
        ghostTag.transform.position = new Vector3(2.5f, 0.4f, 7.5f);

        GameObject ghostBody = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ghostBody.name = "GhostBody";
        ghostBody.transform.SetParent(ghostTag.transform);
        ghostBody.transform.localPosition = Vector3.zero;
        ghostBody.transform.localScale = new Vector3(0.4f, 0.08f, 0.7f);
        ghostBody.GetComponent<Collider>().enabled = false;

        Material ghostMat = new Material(Shader.Find("Standard"));
        ghostMat.SetFloat("_Mode", 3);
        ghostMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        ghostMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        ghostMat.SetInt("_ZWrite", 0);
        ghostMat.EnableKeyword("_ALPHABLEND_ON");
        ghostMat.renderQueue = 3000;
        ghostMat.color = new Color(0f, 0.7f, 1f, 0.6f);
        ghostMat.EnableKeyword("_EMISSION");
        ghostMat.SetColor("_EmissionColor", new Color(0f, 0.5f, 1f));
        ghostBody.GetComponent<Renderer>().sharedMaterial = ghostMat;

        TrailRenderer trail = ghostTag.AddComponent<TrailRenderer>();
        trail.time = 4.0f;
        trail.startWidth = 0.15f;
        trail.endWidth = 0.02f;
        trail.material = new Material(Shader.Find("Sprites/Default"));
        trail.startColor = new Color(0f, 0.8f, 1f, 0.8f);
        trail.endColor = new Color(0f, 0.2f, 1f, 0.0f);

        GameObject ghostHudObj = new GameObject("HUD");
        ghostHudObj.transform.SetParent(ghostTag.transform);
        ghostHudObj.transform.localPosition = new Vector3(0, 1.6f, 0);
        TextMesh ghostTm = ghostHudObj.AddComponent<TextMesh>();
        ghostTm.fontSize = 24;
        ghostTm.characterSize = 0.07f;
        ghostTm.color = new Color(0.3f, 0.8f, 1f);
        ghostTm.alignment = TextAlignment.Center;
        ghostTm.anchor = TextAnchor.MiddleCenter;

        TagVisualizer vis = ghostTag.AddComponent<TagVisualizer>();
        vis.hudText = ghostTm;

        // 9. Attach Bottom Live Telemetry Table HUD
        GameObject tableManager = new GameObject("HUDTableManager");
        tableManager.AddComponent<HUDTableUI>();

        // 10. Camera Controller Setup
        Camera.main.transform.position = new Vector3(5.0f, 11.5f, -2.5f);
        Camera.main.transform.rotation = Quaternion.Euler(60f, 0f, 0f);
        Camera.main.backgroundColor = new Color(0.88f, 0.92f, 0.95f);
        if (Camera.main.GetComponent<CameraController>() == null) {
            CameraController cc = Camera.main.gameObject.AddComponent<CameraController>();
            cc.targetPlayer = trueTag.transform;
        }

        GameObject lightObj = GameObject.Find("Directional Light");
        if (lightObj == null) {
            lightObj = new GameObject("Directional Light");
            Light l = lightObj.AddComponent<Light>();
            l.type = LightType.Directional;
        }
        lightObj.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        Debug.Log("Successfully generated High-Detail Zimbabwean Hospital with Bulletproof Ghost Tag Deserialization!");
    }

    private static void BuildWall(string name, Vector3 pos, Vector3 scale, Material mat)
    {
        GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall.name = name;
        wall.tag = "Obstacle";
        wall.transform.position = pos;
        wall.transform.localScale = scale;
        wall.GetComponent<Renderer>().sharedMaterial = mat;
    }

    private static void BuildWindow(string name, Vector3 pos, Vector3 scale, Material glassMat, Material frameMat)
    {
        GameObject winRoot = new GameObject(name);
        winRoot.transform.position = pos;

        GameObject glass = GameObject.CreatePrimitive(PrimitiveType.Cube);
        glass.name = "GlassPane";
        glass.transform.SetParent(winRoot.transform);
        glass.transform.localPosition = Vector3.zero;
        glass.transform.localScale = scale;
        glass.GetComponent<Renderer>().sharedMaterial = glassMat;

        GameObject frame = GameObject.CreatePrimitive(PrimitiveType.Cube);
        frame.name = "WindowFrame";
        frame.transform.SetParent(winRoot.transform);
        frame.transform.localPosition = Vector3.zero;
        frame.transform.localScale = new Vector3(scale.x + 0.1f, scale.y + 0.1f, 0.04f);
        frame.GetComponent<Renderer>().sharedMaterial = frameMat;
    }

    private static void BuildDoor(string name, Vector3 pos, Material doorMat)
    {
        GameObject door = GameObject.CreatePrimitive(PrimitiveType.Cube);
        door.name = name;
        door.tag = "Obstacle";
        door.transform.position = pos;
        door.transform.localScale = name.Contains("RoomA_to_C") ? new Vector3(1.2f, 2.2f, 0.1f) : new Vector3(0.1f, 2.2f, 1.2f);
        door.GetComponent<Renderer>().sharedMaterial = doorMat;
        door.AddComponent<DoorController>();
    }

    private static void BuildBedWithPatient(string name, Vector3 pos, Material frameMat, Material matMat, Material blanketMat, Material skinMat, string patientName)
    {
        GameObject bed = new GameObject(name);
        bed.transform.position = pos;

        GameObject mattress = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mattress.name = "Mattress_Obstacle";
        mattress.tag = "Obstacle";
        mattress.transform.SetParent(bed.transform);
        mattress.transform.localPosition = new Vector3(0, 0.45f, 0);
        mattress.transform.localScale = new Vector3(1.2f, 0.35f, 2.1f);
        mattress.GetComponent<Renderer>().sharedMaterial = matMat;

        GameObject blanket = GameObject.CreatePrimitive(PrimitiveType.Cube);
        blanket.name = "Blanket";
        blanket.transform.SetParent(bed.transform);
        blanket.transform.localPosition = new Vector3(0, 0.65f, -0.2f);
        blanket.transform.localScale = new Vector3(1.15f, 0.15f, 1.4f);
        blanket.GetComponent<Renderer>().sharedMaterial = blanketMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "PatientHead";
        head.transform.SetParent(bed.transform);
        head.transform.localPosition = new Vector3(0, 0.72f, 0.7f);
        head.transform.localScale = new Vector3(0.35f, 0.35f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(bed.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.3f, 0.7f);
        TextMesh tm = labelObj.AddComponent<TextMesh>();
        tm.text = "🛌 " + patientName;
        tm.fontSize = 20;
        tm.characterSize = 0.06f;
        tm.color = Color.white;
        tm.alignment = TextAlignment.Center;
        tm.anchor = TextAnchor.MiddleCenter;
    }

    private static void CreateWalkingHuman(string name, Vector3 pos, Material outfitMat, Material skinMat, Vector3[] waypoints, string label)
    {
        GameObject human = new GameObject(name);
        human.tag = "Obstacle";
        human.transform.position = pos;

        GameObject body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.name = "OutfitMesh";
        body.transform.SetParent(human.transform);
        body.transform.localPosition = Vector3.zero;
        body.transform.localScale = new Vector3(0.5f, 0.9f, 0.5f);
        body.GetComponent<Renderer>().sharedMaterial = outfitMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "MelaninHeadMesh";
        head.transform.SetParent(human.transform);
        head.transform.localPosition = new Vector3(0, 1.1f, 0);
        head.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(human.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.6f, 0);
        TextMesh tm = labelObj.AddComponent<TextMesh>();
        tm.text = label;
        tm.fontSize = 22;
        tm.characterSize = 0.06f;
        tm.color = new Color(0.2f, 0.2f, 0.8f);
        tm.alignment = TextAlignment.Center;
        tm.anchor = TextAnchor.MiddleCenter;

        HumanWalker walker = human.AddComponent<HumanWalker>();
        walker.waypoints = waypoints;
        walker.labelText = tm;
    }

    private static void CreateSunflowerPot(Vector3 pos, string name, Material potMat, Material stemMat, Material centerMat, Material petalMat)
    {
        GameObject plantRoot = new GameObject(name);
        plantRoot.transform.position = pos;

        GameObject pot = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        pot.transform.SetParent(plantRoot.transform);
        pot.transform.localPosition = new Vector3(0, 0.2f, 0);
        pot.transform.localScale = new Vector3(0.35f, 0.2f, 0.35f);
        pot.GetComponent<Renderer>().sharedMaterial = potMat;

        GameObject stem = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        stem.transform.SetParent(plantRoot.transform);
        stem.transform.localPosition = new Vector3(0, 0.65f, 0);
        stem.transform.localScale = new Vector3(0.04f, 0.3f, 0.04f);
        stem.GetComponent<Renderer>().sharedMaterial = stemMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        head.transform.SetParent(plantRoot.transform);
        head.transform.localPosition = new Vector3(0, 1.0f, 0);
        head.transform.localRotation = Quaternion.Euler(30f, 0, 0);
        head.transform.localScale = new Vector3(0.35f, 0.02f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = centerMat;

        for (int i = 0; i < 8; i++) {
            float angle = i * 45f * Mathf.Deg2Rad;
            GameObject petal = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            petal.transform.SetParent(head.transform);
            petal.transform.localPosition = new Vector3(Mathf.Cos(angle) * 0.2f, 0, Mathf.Sin(angle) * 0.2f);
            petal.transform.localScale = new Vector3(0.12f, 0.06f, 0.12f);
            petal.GetComponent<Renderer>().sharedMaterial = petalMat;
        }
    }
}
#endif
"""

    write_file(os.path.join(scripts_dir, "BLESimulator.cs"), ble_sim_code)
    write_file(os.path.join(scripts_dir, "PlayerController.cs"), player_ctrl_code)
    write_file(os.path.join(scripts_dir, "TagVisualizer.cs"), tag_vis_code)
    write_file(os.path.join(scripts_dir, "DoorController.cs"), door_ctrl_code)
    write_file(os.path.join(scripts_dir, "HUDTableUI.cs"), hud_table_code)
    write_file(os.path.join(scripts_dir, "CameraController.cs"), camera_ctrl_code)
    write_file(os.path.join(scripts_dir, "HumanWalker.cs"), human_walker_code)
    write_file(os.path.join(scripts_dir, "DraggableObstacle.cs"), draggable_code)
    write_file(os.path.join(editor_dir, "SceneBuilder.cs"), scene_builder_code)

    print("Successfully updated build_unity_env.py with Bulletproof Ghost Tag Deserialization!")

if __name__ == "__main__":
    main()
