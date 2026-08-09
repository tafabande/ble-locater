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
            hudText.text = string.Format("\\ud83d\\udcf1 PATIENT TAG (TAG_01)\\nPos: ({0:F2}m, {1:F2}m)", 
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

    # 2. PlayerController.cs — with corrected collision detection
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

            // Raycast-based obstacle check that properly ignores floor plane
            bool blocked = false;
            if (Physics.Raycast(transform.position, moveDir.normalized, out RaycastHit wallHit, moveDir.magnitude + 0.15f))
            {
                if (wallHit.collider.CompareTag("Obstacle") && !wallHit.collider.isTrigger)
                {
                    blocked = true;
                }
            }
            if (!blocked)
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

    # 4. HumanWalker.cs — with procedural limb animation & corrected kinematics
    human_walker_code = """using UnityEngine;
using System.Collections;

public class HumanWalker : MonoBehaviour
{
    public Vector3[] waypoints;
    public float walkSpeed = 1.3f;
    public float pauseTimeAtWaypoint = 2.0f;
    public TextMesh labelText;

    [Header("Procedural Limb References")]
    public Transform leftLeg;
    public Transform rightLeg;
    public Transform leftArm;
    public Transform rightArm;
    public Transform headMesh;

    private int currentWaypointIndex = 0;
    private bool isWalking = false;
    private float walkCycleTimer = 0f;

    void Start()
    {
        AutoFindLimbs();

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

    public void AutoFindLimbs()
    {
        if (leftLeg == null && transform.Find("LeftLeg") != null) leftLeg = transform.Find("LeftLeg");
        if (rightLeg == null && transform.Find("RightLeg") != null) rightLeg = transform.Find("RightLeg");
        if (leftArm == null && transform.Find("LeftArm") != null) leftArm = transform.Find("LeftArm");
        if (rightArm == null && transform.Find("RightArm") != null) rightArm = transform.Find("RightArm");
        if (headMesh == null && transform.Find("MelaninHeadMesh") != null) headMesh = transform.Find("MelaninHeadMesh");
    }

    IEnumerator PatrolRoutine()
    {
        while (true)
        {
            Vector3 targetPos = waypoints[currentWaypointIndex];
            targetPos.y = 0.9f;

            isWalking = true;
            while (Vector3.Distance(new Vector3(transform.position.x, 0, transform.position.z), 
                                     new Vector3(targetPos.x, 0, targetPos.z)) > 0.25f)
            {
                Vector3 rawDir = (targetPos - transform.position);
                // Flatten to XZ plane to prevent Y-component leakage into horizontal movement
                Vector3 dir = new Vector3(rawDir.x, 0f, rawDir.z).normalized;
                
                if (Physics.Raycast(transform.position, dir, out RaycastHit hit, 0.8f))
                {
                    if (!hit.collider.isTrigger && !hit.collider.name.Contains("Door"))
                    {
                        // Use dot product to pick the cross direction that moves towards target
                        Vector3 cross1 = Vector3.Cross(hit.normal, Vector3.up).normalized;
                        Vector3 cross2 = -cross1;
                        Vector3 toTarget = new Vector3(rawDir.x, 0f, rawDir.z).normalized;
                        dir = (Vector3.Dot(cross1, toTarget) >= Vector3.Dot(cross2, toTarget)) ? cross1 : cross2;
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

            isWalking = false;
            yield return new WaitForSeconds(pauseTimeAtWaypoint);
            currentWaypointIndex = (currentWaypointIndex + 1) % waypoints.Length;
        }
    }

    void Update()
    {
        // 1. Procedural Walking Gait Animation (Leg & Arm Swinging)
        if (isWalking)
        {
            walkCycleTimer += Time.deltaTime * walkSpeed * 5.5f;
            float legAngle = Mathf.Sin(walkCycleTimer) * 28.0f;
            float armAngle = Mathf.Sin(walkCycleTimer) * 24.0f;

            if (leftLeg != null) leftLeg.localRotation = Quaternion.Euler(legAngle, 0, 0);
            if (rightLeg != null) rightLeg.localRotation = Quaternion.Euler(-legAngle, 0, 0);

            if (leftArm != null) leftArm.localRotation = Quaternion.Euler(-armAngle, 0, 0);
            if (rightArm != null) rightArm.localRotation = Quaternion.Euler(armAngle, 0, 0);
        }
        else
        {
            // Smoothly return limbs to upright standing idle posture
            if (leftLeg != null) leftLeg.localRotation = Quaternion.Slerp(leftLeg.localRotation, Quaternion.identity, Time.deltaTime * 8.0f);
            if (rightLeg != null) rightLeg.localRotation = Quaternion.Slerp(rightLeg.localRotation, Quaternion.identity, Time.deltaTime * 8.0f);
            if (leftArm != null) leftArm.localRotation = Quaternion.Slerp(leftArm.localRotation, Quaternion.identity, Time.deltaTime * 8.0f);
            if (rightArm != null) rightArm.localRotation = Quaternion.Slerp(rightArm.localRotation, Quaternion.identity, Time.deltaTime * 8.0f);
        }

        // 2. Billboarding floating HUD text towards camera
        if (labelText != null && Camera.main != null)
        {
            labelText.transform.rotation = Quaternion.LookRotation(labelText.transform.position - Camera.main.transform.position);
        }
    }
}
"""

    # 5. DoorController.cs — with dual sliding panels, LED indicator, and smooth easing
    door_ctrl_code = """using UnityEngine;

public class DoorController : MonoBehaviour
{
    [Header("Door Motion Settings")]
    public float openDistance = 2.4f;
    public float openSpeed = 4.5f;
    public Transform leftPanel;
    public Transform rightPanel;
    public Light statusLedLight;
    public Renderer statusLedRenderer;

    private Vector3 closedPosLeft;
    private Vector3 openPosLeft;
    private Vector3 closedPosRight;
    private Vector3 openPosRight;

    private Vector3 singleClosedPos;
    private Vector3 singleOpenPos;

    private Collider doorCollider;
    private float currentOpenFactor = 0f; // 0 = Closed, 1 = Fully Open

    void Start()
    {
        doorCollider = GetComponent<Collider>();

        // Auto-find panels if child objects exist
        if (leftPanel == null && transform.Find("LeftLeaf") != null) leftPanel = transform.Find("LeftLeaf");
        if (rightPanel == null && transform.Find("RightLeaf") != null) rightPanel = transform.Find("RightLeaf");

        if (leftPanel != null && rightPanel != null)
        {
            closedPosLeft = leftPanel.localPosition;
            closedPosRight = rightPanel.localPosition;

            bool isHorizontal = transform.localScale.x > transform.localScale.z;
            Vector3 offset = isHorizontal ? new Vector3(-0.85f, 0, 0) : new Vector3(0, 0, 0.85f);
            openPosLeft = closedPosLeft + offset;
            openPosRight = closedPosRight - offset;
        }
        else
        {
            singleClosedPos = transform.position;
            Vector3 offset = (transform.localScale.x > transform.localScale.z) ? new Vector3(-1.4f, 0, 0) : new Vector3(0, 0, 1.4f);
            singleOpenPos = singleClosedPos + offset;
        }

        // Auto-find LED indicator
        if (statusLedLight == null)
        {
            Transform ledChild = transform.Find("StatusLED");
            if (ledChild != null)
            {
                statusLedLight = ledChild.GetComponent<Light>();
                statusLedRenderer = ledChild.GetComponent<Renderer>();
            }
        }
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
                hit.GetComponent<HumanWalker>() != null ||
                hit.GetComponentInParent<HumanWalker>() != null
            ))
            {
                shouldOpen = true;
                break;
            }
        }

        float targetFactor = shouldOpen ? 1.0f : 0.0f;
        // Smooth damped easing transition
        currentOpenFactor = Mathf.MoveTowards(currentOpenFactor, targetFactor, Time.deltaTime * openSpeed * 0.5f);
        float smoothEased = Mathf.SmoothStep(0f, 1f, currentOpenFactor);

        if (leftPanel != null && rightPanel != null)
        {
            leftPanel.localPosition = Vector3.Lerp(closedPosLeft, openPosLeft, smoothEased);
            rightPanel.localPosition = Vector3.Lerp(closedPosRight, openPosRight, smoothEased);
        }
        else
        {
            transform.position = Vector3.Lerp(singleClosedPos, singleOpenPos, smoothEased);
        }

        // Update Door Status LED light (Red when closed, glowing Green when open)
        Color ledColor = Color.Lerp(new Color(1f, 0.1f, 0.1f), new Color(0.1f, 1f, 0.3f), smoothEased);
        if (statusLedLight != null)
        {
            statusLedLight.color = ledColor;
            statusLedLight.intensity = Mathf.Lerp(0.5f, 1.5f, smoothEased);
        }
        if (statusLedRenderer != null && statusLedRenderer.sharedMaterial != null)
        {
            statusLedRenderer.material.color = ledColor;
            statusLedRenderer.material.SetColor("_EmissionColor", ledColor * (0.5f + smoothEased * 1.5f));
        }

        if (doorCollider != null)
        {
            doorCollider.isTrigger = (currentOpenFactor > 0.4f);
        }
    }
}
"""

    # 6. TagVisualizer.cs — Bulletproof direct JSON parser with room/zone extraction
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
            hudText.text = string.Format("\\ud83c\\udfaf PREDICTED GHOST\\nPos: ({0:F2}m, {1:F2}m)", 
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

    # 7. HUDTableUI.cs — 6 columns with ML Self-Learning badge
    hud_table_code = """using UnityEngine;

public class HUDTableUI : MonoBehaviour
{
    private Transform trueTag;
    private TagVisualizer ghostTag;
    private CameraController camCtrl;
    private GUIStyle headerStyle;
    private GUIStyle valueStyle;
    private GUIStyle buttonStyle;
    private GUIStyle learningBadgeStyle;
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

            learningBadgeStyle = new GUIStyle(GUI.skin.label);
            learningBadgeStyle.fontSize = 10;
            learningBadgeStyle.fontStyle = FontStyle.Bold;
            learningBadgeStyle.normal.textColor = new Color(0.2f, 1.0f, 0.5f);
            learningBadgeStyle.alignment = TextAnchor.MiddleCenter;
        }

        float width = Screen.width;
        float height = 82f;
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

        float colWidth = width / 6f;

        // Column 1: Actual Room & Coordinates
        GUI.Label(new Rect(0 * colWidth, top + 6, colWidth, 20), "\\ud83c\\udfe2 ACTUAL ROOM & LOCATION", headerStyle);
        GUI.Label(new Rect(0 * colWidth, top + 30, colWidth, 30), string.Format("{0}\\n({1:F2}m, {2:F2}m)", actualRoom, trueX, trueZ), valueStyle);

        // Column 2: Ghost Room & Coordinates
        GUI.Label(new Rect(1 * colWidth, top + 6, colWidth, 20), "\\ud83c\\udfaf PREDICTED GHOST LOCATION", headerStyle);
        GUI.Label(new Rect(1 * colWidth, top + 30, colWidth, 30), string.Format("{0}\\n({1:F2}m, {2:F2}m)", ghostRoom, ghostX, ghostZ), valueStyle);

        // Column 3: Real-Time MAE Error Rate
        GUI.Label(new Rect(2 * colWidth, top + 6, colWidth, 20), "\\ud83d\\udccf TRACKING ERROR RATE", headerStyle);
        GUI.Label(new Rect(2 * colWidth, top + 32, colWidth, 30), string.Format("{0:F2} METERS", error), valueStyle);

        // Column 4: Predicted ML Zone
        GUI.Label(new Rect(3 * colWidth, top + 6, colWidth, 20), "\\ud83c\\udff7\\ufe0f PREDICTED ML ZONE", headerStyle);
        GUI.Label(new Rect(3 * colWidth, top + 32, colWidth, 30), zone, valueStyle);

        // Column 5: Runtime Online ML Learning Status
        GUI.Label(new Rect(4 * colWidth, top + 6, colWidth, 20), "\\ud83e\\udde0 RUNTIME ML SELF-LEARNING", headerStyle);
        GUI.Label(new Rect(4 * colWidth, top + 28, colWidth, 20), "\\ud83d\\udfe2 ONLINE ADAPTATION ACTIVE", learningBadgeStyle);
        GUI.Label(new Rect(4 * colWidth, top + 46, colWidth, 25), "Learning ground truth live...", learningBadgeStyle);

        // Column 6: Camera Mode & Switcher Button
        string modeStr = camCtrl != null ? camCtrl.currentMode.ToString().ToUpper() : "OVERVIEW";
        GUI.Label(new Rect(5 * colWidth, top + 6, colWidth, 18), "\\ud83d\\udcf7 VIEW: " + modeStr, headerStyle);
        if (GUI.Button(new Rect(5 * colWidth + 15, top + 28, colWidth - 30, 34), "SWITCH VIEW (C)", buttonStyle))
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

    # 9. DayNightCycle.cs — Dynamic sun/moon cycle with room lighting
    day_night_code = """using UnityEngine;

public class DayNightCycle : MonoBehaviour
{
    [Header("Sun & Atmosphere Controls")]
    public Light sunLight;
    public float dayCycleDurationSeconds = 120f;
    public bool autoRotateSun = true;
    public float timeOfDayNormalized = 0.25f; // 0.25 = 12:00 PM Noon

    [Header("Room Lighting References")]
    public Light[] roomCeilingLights;

    private Color morningSunColor = new Color(1.0f, 0.75f, 0.5f);
    private Color noonSunColor = new Color(1.0f, 0.96f, 0.90f);
    private Color eveningSunColor = new Color(1.0f, 0.5f, 0.25f);
    private Color nightSunColor = new Color(0.15f, 0.2f, 0.35f);

    void Start()
    {
        if (sunLight == null)
        {
            GameObject sunObj = GameObject.Find("Directional Light");
            if (sunObj != null) sunLight = sunObj.GetComponent<Light>();
        }

        if (sunLight != null)
        {
            sunLight.shadows = LightShadows.Soft;
            sunLight.shadowStrength = 0.65f;
        }

        FindRoomLights();
    }

    public void FindRoomLights()
    {
        Light[] allLights = FindObjectsOfType<Light>();
        System.Collections.Generic.List<Light> roomLights = new System.Collections.Generic.List<Light>();
        foreach (var l in allLights)
        {
            if (l.type == LightType.Point || l.type == LightType.Spot)
            {
                if (l.gameObject.name.Contains("Room") || l.gameObject.name.Contains("Ceiling"))
                {
                    roomLights.Add(l);
                }
            }
        }
        roomCeilingLights = roomLights.ToArray();
    }

    void Update()
    {
        if (autoRotateSun)
        {
            timeOfDayNormalized += (Time.deltaTime / dayCycleDurationSeconds);
            if (timeOfDayNormalized > 1.0f) timeOfDayNormalized -= 1.0f;
        }

        float sunAngle = timeOfDayNormalized * 360f - 90f;
        if (sunLight != null)
        {
            sunLight.transform.rotation = Quaternion.Euler(sunAngle, -30f, 0f);

            // Interpolate color and intensity based on sun height
            float sunElevation = Mathf.Sin(timeOfDayNormalized * Mathf.PI * 2f);
            if (sunElevation > 0.3f)
            {
                // Day / Noon
                sunLight.color = Color.Lerp(morningSunColor, noonSunColor, (sunElevation - 0.3f) / 0.7f);
                sunLight.intensity = Mathf.Lerp(0.8f, 1.25f, sunElevation);
            }
            else if (sunElevation > -0.1f)
            {
                // Sunrise / Sunset
                sunLight.color = Color.Lerp(eveningSunColor, morningSunColor, (sunElevation + 0.1f) / 0.4f);
                sunLight.intensity = Mathf.Lerp(0.3f, 0.8f, (sunElevation + 0.1f) / 0.4f);
            }
            else
            {
                // Night
                sunLight.color = nightSunColor;
                sunLight.intensity = 0.15f;
            }
        }

        // Adjust room ceiling lights inversely to outdoor sunlight
        float ceilingIntensity = Mathf.Lerp(1.1f, 0.4f, Mathf.Max(0, Mathf.Sin(timeOfDayNormalized * Mathf.PI * 2f)));
        if (roomCeilingLights != null)
        {
            foreach (var rl in roomCeilingLights)
            {
                if (rl != null) rl.intensity = ceilingIntensity;
            }
        }
    }
}
"""

    # 10. SceneBuilder.cs — Full-featured scene generator with articulated humanoids,
    #     dual sliding doors with LEDs, face features, ceiling lights, beacon glow lights
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

        // 1. Room Floor (10m x 10m Hospital Complex with Tile Grid Material)
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Hospital_Floor_Complex";
        floor.transform.position = new Vector3(5.0f, 0, 5.0f);
        floor.transform.localScale = new Vector3(1.0f, 1, 1.0f);
        Material floorMat = new Material(Shader.Find("Standard"));
        floorMat.color = new Color(0.85f, 0.88f, 0.90f);
        floorMat.SetFloat("_Glossiness", 0.5f);
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

        // Melanin Skin Tone Palettes & Hair Materials
        Material zimDoctorSkin = new Material(Shader.Find("Standard"));
        zimDoctorSkin.color = new Color(0.22f, 0.14f, 0.08f); 

        Material zimNurseSkin = new Material(Shader.Find("Standard"));
        zimNurseSkin.color = new Color(0.25f, 0.16f, 0.10f); 

        Material zimVisitorSkin = new Material(Shader.Find("Standard"));
        zimVisitorSkin.color = new Color(0.20f, 0.12f, 0.07f); 

        Material hairBlackMat = new Material(Shader.Find("Standard"));
        hairBlackMat.color = new Color(0.08f, 0.06f, 0.05f);

        Material doctorCoatMat = new Material(Shader.Find("Standard"));
        doctorCoatMat.color = new Color(0.95f, 0.95f, 0.98f);

        Material nurseMat = new Material(Shader.Find("Standard"));
        nurseMat.color = new Color(0.1f, 0.6f, 0.7f);

        Material visitorMat = new Material(Shader.Find("Standard"));
        visitorMat.color = new Color(0.85f, 0.35f, 0.2f); 

        Material trouserDark = new Material(Shader.Find("Standard"));
        trouserDark.color = new Color(0.15f, 0.18f, 0.25f);

        Material shoeBlack = new Material(Shader.Find("Standard"));
        shoeBlack.color = new Color(0.1f, 0.1f, 0.1f);

        Material eyeWhiteMat = new Material(Shader.Find("Standard"));
        eyeWhiteMat.color = Color.white;

        Material eyePupilMat = new Material(Shader.Find("Standard"));
        eyePupilMat.color = Color.black;

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

        // 3. Interior Isolation Dividing Walls with Animated Dual Sliding Automatic Doors & LED Status
        BuildWall("Wall_Div_H_Left", new Vector3(1.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_Div_H_Right", new Vector3(8.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildSlidingDoorWithLED("SlidingDoor_RoomA_to_C", new Vector3(4.0f, 1.1f, 5.0f), true, doorWoodMat, frameMat);

        BuildWall("Wall_Div_V_Bottom", new Vector3(5.0f, 1.25f, 1.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildWall("Wall_Div_V_Top", new Vector3(5.0f, 1.25f, 8.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildSlidingDoorWithLED("SlidingDoor_RoomA_to_B", new Vector3(5.0f, 1.1f, 6.0f), false, doorWoodMat, frameMat);

        // 4. Room Ceiling Lights Setup (4 Rooms)
        BuildRoomCeilingLight("CeilingLight_RoomA", new Vector3(2.5f, 2.3f, 7.5f));
        BuildRoomCeilingLight("CeilingLight_RoomB", new Vector3(7.5f, 2.3f, 7.5f));
        BuildRoomCeilingLight("CeilingLight_RoomC", new Vector3(2.5f, 2.3f, 2.5f));
        BuildRoomCeilingLight("CeilingLight_RoomD", new Vector3(7.5f, 2.3f, 2.5f));

        // 5. 4-Room Furniture & Realistic Patient Setup with Faces & Hair
        BuildBedWithDetailedPatient("Bed_RoomA", new Vector3(1.4f, 0, 7.5f), bedFrameMat, mattressMat, blanketMat, zimDoctorSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, "Patient Rufaro (ICU Bed A)");
        CreateSunflowerPot(new Vector3(0.5f, 0, 9.5f), "Sunflower_RoomA", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildBedWithDetailedPatient("Bed_RoomB", new Vector3(6.4f, 0, 7.5f), bedFrameMat, mattressMat, blanketMat, zimNurseSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, "Patient Nyasha (Bed B)");
        CreateSunflowerPot(new Vector3(9.5f, 0, 9.5f), "Sunflower_RoomB", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        GameObject deskC = GameObject.CreatePrimitive(PrimitiveType.Cube);
        deskC.name = "Nurse_Desk_RoomC";
        deskC.tag = "Obstacle";
        deskC.transform.position = new Vector3(2.5f, 0.4f, 2.5f);
        deskC.transform.localScale = new Vector3(1.8f, 0.8f, 0.8f);
        deskC.GetComponent<Renderer>().sharedMaterial = woodMat;
        deskC.AddComponent<DraggableObstacle>();
        CreateSunflowerPot(new Vector3(0.5f, 0, 0.5f), "Sunflower_RoomC", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildBedWithDetailedPatient("Emergency_Bed_RoomD", new Vector3(8.5f, 0, 2.5f), bedFrameMat, mattressMat, blanketMat, zimVisitorSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, "Emergency Triage Bed");
        CreateSunflowerPot(new Vector3(9.5f, 0, 0.5f), "Sunflower_RoomD", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        // 6. 12 Beacon Anchors (3 per room) with Dynamic Emitter Glow Lights
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

            // Beacon Point Light
            GameObject beaconLightObj = new GameObject("BeaconGlowLight");
            beaconLightObj.transform.SetParent(emitter.transform);
            beaconLightObj.transform.localPosition = Vector3.zero;
            Light bl = beaconLightObj.AddComponent<Light>();
            bl.type = LightType.Point;
            bl.color = new Color(0f, 0.9f, 0.6f);
            bl.intensity = 0.8f;
            bl.range = 3.5f;

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

        // 7. Detailed 3D Humanoid Entities (Legs, Arms, Hair, Face Features & Walking Animation)
        CreateRealisticHumanoid("Dr_Tendai", new Vector3(2.5f, 0.9f, 2.5f), doctorCoatMat, trouserDark, zimDoctorSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(2.5f, 0.9f, 2.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 2.5f)
        }, "\\ud83d\\udc68\\u200d\\u2695\\ufe0f Dr. Tendai (Consultant)", true, false);

        CreateRealisticHumanoid("Nurse_Chipo", new Vector3(7.5f, 0.9f, 2.5f), nurseMat, nurseMat, zimNurseSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(7.5f, 0.9f, 2.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 2.5f)
        }, "\\ud83d\\udc69\\u200d\\u2695\\ufe0f Nurse Chipo (Ward Lead)", false, true);

        CreateRealisticHumanoid("Visitor_Farai", new Vector3(6.5f, 0.9f, 6.5f), visitorMat, trouserDark, zimVisitorSkin, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(6.5f, 0.9f, 6.5f), new Vector3(3.0f, 0.9f, 3.0f), new Vector3(8.0f, 0.9f, 3.0f), new Vector3(6.5f, 0.9f, 6.5f)
        }, "\\ud83c\\udfc3 Visitor Farai", false, false);

        // 8. Patient Smartphone Tag Device (True Tag)
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

        // 9. Predicted Holographic Tag Device (Ghost Tag)
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

        // 10. Attach Bottom Live Telemetry Table HUD
        GameObject tableManager = new GameObject("HUDTableManager");
        tableManager.AddComponent<HUDTableUI>();

        // 11. Camera & Dynamic Lighting Controller Setup
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
        Light mainSun = lightObj.GetComponent<Light>();
        mainSun.shadows = LightShadows.Soft;

        // Attach DayNightCycle to main light
        if (lightObj.GetComponent<DayNightCycle>() == null) {
            lightObj.AddComponent<DayNightCycle>();
        }

        Debug.Log("Successfully generated High-Detail Zimbabwean Hospital with Realistic 3D People, Smooth LED Doors & Dynamic Lighting!");
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

    private static void BuildRoomCeilingLight(string name, Vector3 pos)
    {
        GameObject lightRoot = new GameObject(name);
        lightRoot.transform.position = pos;

        GameObject fixture = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        fixture.transform.SetParent(lightRoot.transform);
        fixture.transform.localPosition = Vector3.zero;
        fixture.transform.localScale = new Vector3(0.5f, 0.05f, 0.5f);
        Material fixMat = new Material(Shader.Find("Standard"));
        fixMat.color = new Color(0.9f, 0.95f, 1.0f);
        fixMat.EnableKeyword("_EMISSION");
        fixMat.SetColor("_EmissionColor", new Color(0.8f, 0.85f, 0.9f));
        fixture.GetComponent<Renderer>().sharedMaterial = fixMat;

        Light pointL = lightRoot.AddComponent<Light>();
        pointL.type = LightType.Point;
        pointL.color = new Color(0.95f, 0.95f, 1.0f);
        pointL.intensity = 0.9f;
        pointL.range = 8.0f;
        pointL.shadows = LightShadows.Soft;
    }

    private static void BuildSlidingDoorWithLED(string name, Vector3 pos, bool isHorizontal, Material doorMat, Material frameMat)
    {
        GameObject doorRoot = new GameObject(name);
        doorRoot.tag = "Obstacle";
        doorRoot.transform.position = pos;

        BoxCollider mainCol = doorRoot.AddComponent<BoxCollider>();
        mainCol.size = isHorizontal ? new Vector3(1.8f, 2.2f, 0.3f) : new Vector3(0.3f, 2.2f, 1.8f);

        // Top Frame Track
        GameObject track = GameObject.CreatePrimitive(PrimitiveType.Cube);
        track.name = "DoorTrackFrame";
        track.transform.SetParent(doorRoot.transform);
        track.transform.localPosition = new Vector3(0, 1.15f, 0);
        track.transform.localScale = isHorizontal ? new Vector3(1.9f, 0.12f, 0.2f) : new Vector3(0.2f, 0.12f, 1.9f);
        track.GetComponent<Renderer>().sharedMaterial = frameMat;

        // LED Indicator Light
        GameObject led = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        led.name = "StatusLED";
        led.transform.SetParent(doorRoot.transform);
        led.transform.localPosition = new Vector3(0, 1.25f, 0);
        led.transform.localScale = new Vector3(0.12f, 0.12f, 0.12f);
        Material ledMat = new Material(Shader.Find("Standard"));
        ledMat.color = new Color(1f, 0.1f, 0.1f);
        ledMat.EnableKeyword("_EMISSION");
        ledMat.SetColor("_EmissionColor", new Color(1f, 0.1f, 0.1f));
        led.GetComponent<Renderer>().sharedMaterial = ledMat;

        Light ledLight = led.AddComponent<Light>();
        ledLight.type = LightType.Point;
        ledLight.color = new Color(1f, 0.1f, 0.1f);
        ledLight.intensity = 0.6f;
        ledLight.range = 1.5f;

        // Left Sliding Leaf
        GameObject leftLeaf = GameObject.CreatePrimitive(PrimitiveType.Cube);
        leftLeaf.name = "LeftLeaf";
        leftLeaf.transform.SetParent(doorRoot.transform);
        leftLeaf.transform.localPosition = isHorizontal ? new Vector3(-0.42f, 0, 0) : new Vector3(0, 0, -0.42f);
        leftLeaf.transform.localScale = isHorizontal ? new Vector3(0.85f, 2.1f, 0.08f) : new Vector3(0.08f, 2.1f, 0.85f);
        leftLeaf.GetComponent<Renderer>().sharedMaterial = doorMat;

        // Right Sliding Leaf
        GameObject rightLeaf = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rightLeaf.name = "RightLeaf";
        rightLeaf.transform.SetParent(doorRoot.transform);
        rightLeaf.transform.localPosition = isHorizontal ? new Vector3(0.42f, 0, 0) : new Vector3(0, 0, 0.42f);
        rightLeaf.transform.localScale = isHorizontal ? new Vector3(0.85f, 2.1f, 0.08f) : new Vector3(0.08f, 2.1f, 0.85f);
        rightLeaf.GetComponent<Renderer>().sharedMaterial = doorMat;

        DoorController controller = doorRoot.AddComponent<DoorController>();
        controller.leftPanel = leftLeaf.transform;
        controller.rightPanel = rightLeaf.transform;
        controller.statusLedLight = ledLight;
        controller.statusLedRenderer = led.GetComponent<Renderer>();
    }

    private static void BuildBedWithDetailedPatient(string name, Vector3 pos, Material frameMat, Material matMat, Material blanketMat, Material skinMat, Material hairMat, Material eyeWhiteMat, Material eyePupilMat, string patientName)
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

        // Pillow under head
        GameObject pillow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        pillow.name = "Pillow";
        pillow.transform.SetParent(bed.transform);
        pillow.transform.localPosition = new Vector3(0, 0.65f, 0.7f);
        pillow.transform.localScale = new Vector3(0.8f, 0.12f, 0.45f);

        GameObject blanket = GameObject.CreatePrimitive(PrimitiveType.Cube);
        blanket.name = "Blanket";
        blanket.transform.SetParent(bed.transform);
        blanket.transform.localPosition = new Vector3(0, 0.65f, -0.2f);
        blanket.transform.localScale = new Vector3(1.15f, 0.15f, 1.4f);
        blanket.GetComponent<Renderer>().sharedMaterial = blanketMat;

        // Detailed Patient Head with Face Features & Hair
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "PatientHead";
        head.transform.SetParent(bed.transform);
        head.transform.localPosition = new Vector3(0, 0.75f, 0.7f);
        head.transform.localScale = new Vector3(0.35f, 0.35f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        BuildFaceFeatures(head.transform, eyeWhiteMat, eyePupilMat, skinMat, hairMat);

        // Resting arms on blanket
        GameObject leftArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        leftArm.transform.SetParent(bed.transform);
        leftArm.transform.localPosition = new Vector3(-0.45f, 0.72f, 0.2f);
        leftArm.transform.localRotation = Quaternion.Euler(0, 0, 10f);
        leftArm.transform.localScale = new Vector3(0.08f, 0.35f, 0.08f);
        leftArm.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject rightArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rightArm.transform.SetParent(bed.transform);
        rightArm.transform.localPosition = new Vector3(0.45f, 0.72f, 0.2f);
        rightArm.transform.localRotation = Quaternion.Euler(0, 0, -10f);
        rightArm.transform.localScale = new Vector3(0.08f, 0.35f, 0.08f);
        rightArm.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(bed.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.3f, 0.7f);
        TextMesh tm = labelObj.AddComponent<TextMesh>();
        tm.text = "\\ud83d\\udecf\\ufe0f " + patientName;
        tm.fontSize = 20;
        tm.characterSize = 0.06f;
        tm.color = Color.white;
        tm.alignment = TextAlignment.Center;
        tm.anchor = TextAnchor.MiddleCenter;
    }

    private static void CreateRealisticHumanoid(string name, Vector3 pos, Material outfitMat, Material trouserMat, Material skinMat, Material hairMat, Material eyeWhiteMat, Material eyePupilMat, Material shoeMat, Vector3[] waypoints, string label, bool isDoctor, bool isNurse)
    {
        GameObject human = new GameObject(name);
        human.tag = "Obstacle";
        human.transform.position = pos;

        // 1. Torso / Chest
        GameObject chest = GameObject.CreatePrimitive(PrimitiveType.Cube);
        chest.name = "ChestTorso";
        chest.transform.SetParent(human.transform);
        chest.transform.localPosition = new Vector3(0, 0.95f, 0);
        chest.transform.localScale = new Vector3(0.45f, 0.55f, 0.26f);
        chest.GetComponent<Renderer>().sharedMaterial = outfitMat;

        // Doctor Stethoscope details
        if (isDoctor)
        {
            GameObject steth = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            steth.name = "Stethoscope";
            steth.transform.SetParent(chest.transform);
            steth.transform.localPosition = new Vector3(0, 0.1f, 0.52f);
            steth.transform.localScale = new Vector3(0.35f, 0.05f, 0.35f);
            Material stethMat = new Material(Shader.Find("Standard"));
            stethMat.color = Color.black;
            steth.GetComponent<Renderer>().sharedMaterial = stethMat;
        }

        // 2. Neck
        GameObject neck = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        neck.name = "Neck";
        neck.transform.SetParent(human.transform);
        neck.transform.localPosition = new Vector3(0, 1.26f, 0);
        neck.transform.localScale = new Vector3(0.12f, 0.08f, 0.12f);
        neck.GetComponent<Renderer>().sharedMaterial = skinMat;

        // 3. Head & Facial Features
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "MelaninHeadMesh";
        head.transform.SetParent(human.transform);
        head.transform.localPosition = new Vector3(0, 1.45f, 0);
        head.transform.localScale = new Vector3(0.35f, 0.35f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        BuildFaceFeatures(head.transform, eyeWhiteMat, eyePupilMat, skinMat, hairMat);

        // 4. Left Arm Joint Pivot & Mesh
        GameObject leftArmPivot = new GameObject("LeftArm");
        leftArmPivot.transform.SetParent(human.transform);
        leftArmPivot.transform.localPosition = new Vector3(-0.28f, 1.15f, 0);

        GameObject lUpperArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        lUpperArm.transform.SetParent(leftArmPivot.transform);
        lUpperArm.transform.localPosition = new Vector3(0, -0.16f, 0);
        lUpperArm.transform.localScale = new Vector3(0.1f, 0.16f, 0.1f);
        lUpperArm.GetComponent<Renderer>().sharedMaterial = outfitMat;

        GameObject lHand = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lHand.transform.SetParent(leftArmPivot.transform);
        lHand.transform.localPosition = new Vector3(0, -0.34f, 0);
        lHand.transform.localScale = new Vector3(0.11f, 0.11f, 0.11f);
        lHand.GetComponent<Renderer>().sharedMaterial = skinMat;

        // 5. Right Arm Joint Pivot & Mesh
        GameObject rightArmPivot = new GameObject("RightArm");
        rightArmPivot.transform.SetParent(human.transform);
        rightArmPivot.transform.localPosition = new Vector3(0.28f, 1.15f, 0);

        GameObject rUpperArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rUpperArm.transform.SetParent(rightArmPivot.transform);
        rUpperArm.transform.localPosition = new Vector3(0, -0.16f, 0);
        rUpperArm.transform.localScale = new Vector3(0.1f, 0.16f, 0.1f);
        rUpperArm.GetComponent<Renderer>().sharedMaterial = outfitMat;

        GameObject rHand = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rHand.transform.SetParent(rightArmPivot.transform);
        rHand.transform.localPosition = new Vector3(0, -0.34f, 0);
        rHand.transform.localScale = new Vector3(0.11f, 0.11f, 0.11f);
        rHand.GetComponent<Renderer>().sharedMaterial = skinMat;

        // 6. Left Leg Joint Pivot & Mesh
        GameObject leftLegPivot = new GameObject("LeftLeg");
        leftLegPivot.transform.SetParent(human.transform);
        leftLegPivot.transform.localPosition = new Vector3(-0.13f, 0.68f, 0);

        GameObject lThigh = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        lThigh.transform.SetParent(leftLegPivot.transform);
        lThigh.transform.localPosition = new Vector3(0, -0.3f, 0);
        lThigh.transform.localScale = new Vector3(0.13f, 0.3f, 0.13f);
        lThigh.GetComponent<Renderer>().sharedMaterial = trouserMat;

        GameObject lShoe = GameObject.CreatePrimitive(PrimitiveType.Cube);
        lShoe.transform.SetParent(leftLegPivot.transform);
        lShoe.transform.localPosition = new Vector3(0, -0.62f, 0.05f);
        lShoe.transform.localScale = new Vector3(0.14f, 0.08f, 0.22f);
        lShoe.GetComponent<Renderer>().sharedMaterial = shoeMat;

        // 7. Right Leg Joint Pivot & Mesh
        GameObject rightLegPivot = new GameObject("RightLeg");
        rightLegPivot.transform.SetParent(human.transform);
        rightLegPivot.transform.localPosition = new Vector3(0.13f, 0.68f, 0);

        GameObject rThigh = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rThigh.transform.SetParent(rightLegPivot.transform);
        rThigh.transform.localPosition = new Vector3(0, -0.3f, 0);
        rThigh.transform.localScale = new Vector3(0.13f, 0.3f, 0.13f);
        rThigh.GetComponent<Renderer>().sharedMaterial = trouserMat;

        GameObject rShoe = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rShoe.transform.SetParent(rightLegPivot.transform);
        rShoe.transform.localPosition = new Vector3(0, -0.62f, 0.05f);
        rShoe.transform.localScale = new Vector3(0.14f, 0.08f, 0.22f);
        rShoe.GetComponent<Renderer>().sharedMaterial = shoeMat;

        // Floating HUD Label
        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(human.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.85f, 0);
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
        walker.leftLeg = leftLegPivot.transform;
        walker.rightLeg = rightLegPivot.transform;
        walker.leftArm = leftArmPivot.transform;
        walker.rightArm = rightArmPivot.transform;
        walker.headMesh = head.transform;
    }

    private static void BuildFaceFeatures(Transform headTransform, Material eyeWhiteMat, Material eyePupilMat, Material skinMat, Material hairMat)
    {
        // 1. Left Eye
        GameObject lEyeWhite = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lEyeWhite.name = "LeftEyeWhite";
        lEyeWhite.transform.SetParent(headTransform);
        lEyeWhite.transform.localPosition = new Vector3(-0.16f, 0.08f, 0.42f);
        lEyeWhite.transform.localScale = new Vector3(0.18f, 0.18f, 0.12f);
        lEyeWhite.GetComponent<Renderer>().sharedMaterial = eyeWhiteMat;

        GameObject lPupil = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lPupil.name = "LeftPupil";
        lPupil.transform.SetParent(lEyeWhite.transform);
        lPupil.transform.localPosition = new Vector3(0, 0, 0.45f);
        lPupil.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f);
        lPupil.GetComponent<Renderer>().sharedMaterial = eyePupilMat;

        // 2. Right Eye
        GameObject rEyeWhite = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rEyeWhite.name = "RightEyeWhite";
        rEyeWhite.transform.SetParent(headTransform);
        rEyeWhite.transform.localPosition = new Vector3(0.16f, 0.08f, 0.42f);
        rEyeWhite.transform.localScale = new Vector3(0.18f, 0.18f, 0.12f);
        rEyeWhite.GetComponent<Renderer>().sharedMaterial = eyeWhiteMat;

        GameObject rPupil = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rPupil.name = "RightPupil";
        rPupil.transform.SetParent(rEyeWhite.transform);
        rPupil.transform.localPosition = new Vector3(0, 0, 0.45f);
        rPupil.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f);
        rPupil.GetComponent<Renderer>().sharedMaterial = eyePupilMat;

        // 3. Eyebrows
        GameObject lBrow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        lBrow.transform.SetParent(headTransform);
        lBrow.transform.localPosition = new Vector3(-0.16f, 0.22f, 0.42f);
        lBrow.transform.localScale = new Vector3(0.22f, 0.04f, 0.06f);
        lBrow.GetComponent<Renderer>().sharedMaterial = hairMat;

        GameObject rBrow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rBrow.transform.SetParent(headTransform);
        rBrow.transform.localPosition = new Vector3(0.16f, 0.22f, 0.42f);
        rBrow.transform.localScale = new Vector3(0.22f, 0.04f, 0.06f);
        rBrow.GetComponent<Renderer>().sharedMaterial = hairMat;

        // 4. Nose
        GameObject nose = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nose.name = "Nose";
        nose.transform.SetParent(headTransform);
        nose.transform.localPosition = new Vector3(0, -0.04f, 0.48f);
        nose.transform.localScale = new Vector3(0.1f, 0.14f, 0.12f);
        nose.GetComponent<Renderer>().sharedMaterial = skinMat;

        // 5. Mouth / Lips
        GameObject mouth = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mouth.name = "Lips";
        mouth.transform.SetParent(headTransform);
        mouth.transform.localPosition = new Vector3(0, -0.22f, 0.44f);
        mouth.transform.localScale = new Vector3(0.22f, 0.06f, 0.06f);
        Material lipMat = new Material(Shader.Find("Standard"));
        lipMat.color = new Color(0.35f, 0.18f, 0.15f);
        mouth.GetComponent<Renderer>().sharedMaterial = lipMat;

        // 6. Styled Hair Cluster (Afro / Textured Hair Spheres)
        GameObject hairCluster = new GameObject("HairMeshCluster");
        hairCluster.transform.SetParent(headTransform);
        hairCluster.transform.localPosition = Vector3.zero;

        Vector3[] hairOffsets = {
            new Vector3(0, 0.28f, -0.05f), new Vector3(-0.18f, 0.24f, 0), new Vector3(0.18f, 0.24f, 0),
            new Vector3(0, 0.26f, 0.15f), new Vector3(-0.12f, 0.26f, -0.16f), new Vector3(0.12f, 0.26f, -0.16f)
        };
        foreach (var offset in hairOffsets)
        {
            GameObject puff = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            puff.transform.SetParent(hairCluster.transform);
            puff.transform.localPosition = offset;
            puff.transform.localScale = new Vector3(0.55f, 0.55f, 0.55f);
            puff.GetComponent<Renderer>().sharedMaterial = hairMat;
        }
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
    write_file(os.path.join(scripts_dir, "DayNightCycle.cs"), day_night_code)
    write_file(os.path.join(editor_dir, "SceneBuilder.cs"), scene_builder_code)

    print("\nSuccessfully generated all 10 scripts with full-featured Unity scene!")
    print("  - Dual sliding doors with LED status indicators")
    print("  - Articulated humanoids with face features & walking animation")
    print("  - DayNightCycle dynamic lighting system")
    print("  - Room ceiling lights with beacon glow lights")
    print("  - 6-column HUD with ML Self-Learning badge")
    print("  - Corrected kinematics (obstacle avoidance, collision, gait)")

if __name__ == "__main__":
    main()
