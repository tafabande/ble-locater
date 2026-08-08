using UnityEngine;
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
    public float pathLossExponentClear = 2.7f;
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
            hudText.text = string.Format("📱 PATIENT TAG (TAG_01)\nPos: ({0:F2}m, {1:F2}m)", 
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
