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

    print(f"Generating Unity environment in: {base_dir}")

    # 1. BLESimulator.cs (Handles dragging, obstacles, noise, and POSTing data)
    ble_sim_code = """using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;

[System.Serializable]
public class RawPacket {
    public long timestamp;
    public string anchor;
    public string mac;
    public int rssi;
    public string name;
}

public class BLESimulator : MonoBehaviour
{
    [Header("Network Settings")]
    public string backendUrl = "http://127.0.0.1:8000/api/observation";
    public string macAddress = "52:06:26:03:01:DA";
    public float updateRateHz = 10f;

    [Header("Simulation Parameters")]
    public float txPowerAt1m = -55.0f;
    public float pathLossExponentClear = 2.0f;
    public float pathLossExponentObstacle = 3.5f; // Higher decay through walls
    public float noiseStdDev = 1.5f;

    private Transform[] anchors;
    private string[] anchorIds = { "ANCHOR_01", "ANCHOR_02", "ANCHOR_03" };

    // Mouse drag state
    private Vector3 mOffset;
    private float mZCoord;

    void Start()
    {
        // Find anchors in the scene
        anchors = new Transform[3];
        anchors[0] = GameObject.Find("ANCHOR_01")?.transform;
        anchors[1] = GameObject.Find("ANCHOR_02")?.transform;
        anchors[2] = GameObject.Find("ANCHOR_03")?.transform;

        StartCoroutine(SimulateAndSend());
    }

    void OnMouseDown()
    {
        mZCoord = Camera.main.WorldToScreenPoint(gameObject.transform.position).z;
        mOffset = gameObject.transform.position - GetMouseAsWorldPoint();
    }

    private Vector3 GetMouseAsWorldPoint()
    {
        Vector3 mousePoint = Input.mousePosition;
        mousePoint.z = mZCoord;
        return Camera.main.ScreenToWorldPoint(mousePoint);
    }

    void OnMouseDrag()
    {
        Vector3 newPos = GetMouseAsWorldPoint() + mOffset;
        // Keep it on the floor
        newPos.y = 0.5f; 
        transform.position = newPos;
    }

    IEnumerator SimulateAndSend()
    {
        while (true)
        {
            long timestamp = System.DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

            for (int i = 0; i < 3; i++)
            {
                if (anchors[i] == null) continue;

                Vector3 toAnchor = anchors[i].position - transform.position;
                float distance = toAnchor.magnitude;
                if (distance < 0.1f) distance = 0.1f;

                // Raycast to check for obstacles
                float currentPathLoss = pathLossExponentClear;
                if (Physics.Raycast(transform.position, toAnchor.normalized, out RaycastHit hit, distance))
                {
                    if (hit.collider.CompareTag("Obstacle"))
                    {
                        currentPathLoss = pathLossExponentObstacle;
                        // Debug visual for hitting an obstacle (Red line)
                        Debug.DrawRay(transform.position, toAnchor, Color.red, 0.1f);
                    }
                }
                else
                {
                    // Debug visual for clear line of sight (Green line)
                    Debug.DrawRay(transform.position, toAnchor, Color.green, 0.1f);
                }

                // Calculate RSSI
                float rssiFloat = txPowerAt1m - 10f * currentPathLoss * Mathf.Log10(distance);
                
                // Add Gaussian Noise (Box-Muller transform)
                float u1 = 1.0f - Random.value;
                float u2 = 1.0f - Random.value;
                float randStdNormal = Mathf.Sqrt(-2.0f * Mathf.Log(u1)) * Mathf.Sin(2.0f * Mathf.PI * u2);
                float noise = noiseStdDev * randStdNormal;

                int finalRssi = Mathf.RoundToInt(Mathf.Clamp(rssiFloat + noise, -100f, -30f));

                // Send Packet
                RawPacket packet = new RawPacket {
                    timestamp = timestamp,
                    anchor = anchorIds[i],
                    mac = macAddress,
                    rssi = finalRssi,
                    name = "SIMULATED_TAG"
                };

                string json = JsonUtility.ToJson(packet);
                StartCoroutine(PostRequest(backendUrl, json));
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

    # 2. TagVisualizer.cs (Receives WebSocket predictions and moves the ghost)
    tag_vis_code = """using UnityEngine;
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
                    string safeJson = json.Replace("\\"event\\":", "\\"eventName\\":");
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
"""

    # 3. SceneBuilder.cs (Editor script to generate the scene automatically)
    scene_builder_code = """#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class SceneBuilder : EditorWindow
{
    [MenuItem("BLE Demo/Generate Interactive Scene")]
    public static void GenerateScene()
    {
        // Create new empty scene
        EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // 1. Create Floor
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.position = new Vector3(2.5f, 0, 2f);
        floor.transform.localScale = new Vector3(2, 1, 2);
        
        Material floorMat = new Material(Shader.Find("Standard"));
        floorMat.color = new Color(0.2f, 0.2f, 0.2f);
        floor.GetComponent<Renderer>().sharedMaterial = floorMat;

        // 2. Add Tag "Obstacle" to Unity Tag Manager if it doesn't exist
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

        // 3. Create Obstacles (Walls)
        Material wallMat = new Material(Shader.Find("Standard"));
        wallMat.color = new Color(0.8f, 0.4f, 0.1f); // Orange walls

        GameObject wall1 = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall1.name = "Wall_1";
        wall1.tag = "Obstacle";
        wall1.transform.position = new Vector3(2.5f, 1f, 1.5f);
        wall1.transform.localScale = new Vector3(2f, 2f, 0.2f);
        wall1.GetComponent<Renderer>().sharedMaterial = wallMat;

        GameObject wall2 = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall2.name = "Wall_2";
        wall2.tag = "Obstacle";
        wall2.transform.position = new Vector3(1.5f, 1f, 3f);
        wall2.transform.localScale = new Vector3(0.2f, 2f, 1.5f);
        wall2.GetComponent<Renderer>().sharedMaterial = wallMat;

        // 4. Create Anchors
        Vector3[] anchorPositions = { new Vector3(0, 0, 0), new Vector3(5, 0, 0), new Vector3(2.5f, 0, 4.33f) };
        Material anchorMat = new Material(Shader.Find("Standard"));
        anchorMat.color = Color.black;

        for (int i = 0; i < 3; i++) {
            GameObject anchor = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            anchor.name = "ANCHOR_0" + (i + 1);
            anchor.transform.position = anchorPositions[i];
            anchor.transform.localScale = new Vector3(0.3f, 1f, 0.3f);
            anchor.GetComponent<Renderer>().sharedMaterial = anchorMat;
        }

        // 5. Create True Interactive Tag
        GameObject trueTag = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        trueTag.name = "True_Tag (Drag Me)";
        trueTag.transform.position = new Vector3(2.5f, 0.5f, 0.5f);
        Material trueTagMat = new Material(Shader.Find("Standard"));
        trueTagMat.color = Color.red;
        trueTag.GetComponent<Renderer>().sharedMaterial = trueTagMat;
        trueTag.AddComponent<BLESimulator>(); // Attach interactivity and simulation

        // 6. Create Ghost Tag (Predicted by Python)
        GameObject ghostTag = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        ghostTag.name = "Ghost_Tag (Predicted)";
        ghostTag.transform.position = new Vector3(2.5f, 0.5f, 0.5f);
        Material ghostMat = new Material(Shader.Find("Standard"));
        // Make it transparent blue
        ghostMat.SetFloat("_Mode", 3); // Transparent mode
        ghostMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        ghostMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        ghostMat.SetInt("_ZWrite", 0);
        ghostMat.DisableKeyword("_ALPHATEST_ON");
        ghostMat.EnableKeyword("_ALPHABLEND_ON");
        ghostMat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        ghostMat.renderQueue = 3000;
        ghostMat.color = new Color(0f, 0.5f, 1f, 0.5f); 
        
        ghostTag.GetComponent<Renderer>().sharedMaterial = ghostMat;
        // Disable collider so it doesn't block rays
        ghostTag.GetComponent<Collider>().enabled = false;
        ghostTag.AddComponent<TagVisualizer>();

        // 7. Setup Camera
        Camera.main.transform.position = new Vector3(2.5f, 7f, -3f);
        Camera.main.transform.rotation = Quaternion.Euler(60f, 0f, 0f);

        Debug.Log("Successfully generated BLE Interactive Simulation Scene!");
    }
}
#endif
"""

    write_file(os.path.join(scripts_dir, "BLESimulator.cs"), ble_sim_code)
    write_file(os.path.join(scripts_dir, "TagVisualizer.cs"), tag_vis_code)
    write_file(os.path.join(editor_dir, "SceneBuilder.cs"), scene_builder_code)

    print("All files generated successfully!")

if __name__ == "__main__":
    main()
