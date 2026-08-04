using UnityEngine;
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
