using UnityEngine;
using UnityEngine.UI;
using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;

// Data structure for parsing Geofence Alert WebSocket payloads
[Serializable]
public class AlertPayload {
    public string type;
    public string severity;
    public string patient;
    public string from;
    public string to;
    public string time;
    public string message;
}

[Serializable]
public class PositionUpdateAlertData {
    public PosData position;
    public AlertPayload alert;
}

[Serializable]
public class WSAlertEvent {
    public string eventName;
    public PositionUpdateAlertData data;
}

public class GeofenceAlertBanner : MonoBehaviour
{
    [Header("UI Component References")]
    public GameObject bannerPanel;
    public Text alertText;
    public Image alertIconBackground;

    [Header("Severity Colors")]
    public Color highSeverityColor = new Color(0.95f, 0.35f, 0.40f, 0.95f);
    public Color warningSeverityColor = new Color(0.98f, 0.70f, 0.50f, 0.95f);
    public Color infoSeverityColor = new Color(0.54f, 0.70f, 0.98f, 0.95f);

    [Header("Display Settings")]
    public float autoHideSeconds = 5.0f;

    private string pendingAlertMsg = "";
    private string pendingSeverity = "";
    private bool hasNewAlert = false;
    private float hideTimer = 0.0f;

    void Start()
    {
        if (bannerPanel != null) {
            bannerPanel.SetActive(false);
        }
    }

    void Update()
    {
        // Thread-safe update from WebSocket background thread
        if (hasNewAlert) {
            ShowBanner(pendingAlertMsg, pendingSeverity);
            hasNewAlert = false;
        }

        if (bannerPanel != null && bannerPanel.activeSelf) {
            hideTimer -= Time.deltaTime;
            if (hideTimer <= 0.0f) {
                bannerPanel.SetActive(false);
            }
        }
    }

    public void TriggerAlert(string message, string severity) {
        pendingAlertMsg = message;
        pendingSeverity = severity;
        hasNewAlert = true;
    }

    private void ShowBanner(string msg, string severity) {
        if (bannerPanel == null || alertText == null) return;

        alertText.text = msg;
        if (alertIconBackground != null) {
            if (severity == "HIGH") alertIconBackground.color = highSeverityColor;
            else if (severity == "WARNING") alertIconBackground.color = warningSeverityColor;
            else alertIconBackground.color = infoSeverityColor;
        }

        bannerPanel.SetActive(true);
        hideTimer = autoHideSeconds;
        Debug.LogWarning("[GEOFENCE ALERT BANNER] " + msg);
    }
}
