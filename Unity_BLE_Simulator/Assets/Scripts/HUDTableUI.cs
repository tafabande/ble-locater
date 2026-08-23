using UnityEngine;

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
        if (x < 5.0f && z >= 5.0f) return "Room A (Executive Suite 1)";
        if (x >= 5.0f && z >= 5.0f) return "Room B (Meeting Room 2)";
        if (x < 5.0f && z < 5.0f) return "Room C (Operations Hub)";
        return "Room D (Main Entrance)";
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
        GUI.Label(new Rect(0 * colWidth, top + 6, colWidth, 20), "\ud83c\udfe2 ACTUAL ROOM & LOCATION", headerStyle);
        GUI.Label(new Rect(0 * colWidth, top + 30, colWidth, 30), string.Format("{0}\n({1:F2}m, {2:F2}m)", actualRoom, trueX, trueZ), valueStyle);

        // Column 2: Ghost Room & Coordinates
        GUI.Label(new Rect(1 * colWidth, top + 6, colWidth, 20), "\ud83c\udfaf PREDICTED GHOST LOCATION", headerStyle);
        GUI.Label(new Rect(1 * colWidth, top + 30, colWidth, 30), string.Format("{0}\n({1:F2}m, {2:F2}m)", ghostRoom, ghostX, ghostZ), valueStyle);

        // Column 3: Real-Time MAE Error Rate
        GUI.Label(new Rect(2 * colWidth, top + 6, colWidth, 20), "\ud83d\udccf TRACKING ERROR RATE", headerStyle);
        GUI.Label(new Rect(2 * colWidth, top + 32, colWidth, 30), string.Format("{0:F2} METERS", error), valueStyle);

        // Column 4: Predicted ML Zone
        GUI.Label(new Rect(3 * colWidth, top + 6, colWidth, 20), "\ud83c\udff7\ufe0f PREDICTED ML ZONE", headerStyle);
        GUI.Label(new Rect(3 * colWidth, top + 32, colWidth, 30), zone, valueStyle);

        // Column 5: Runtime Online ML Learning Status
        GUI.Label(new Rect(4 * colWidth, top + 6, colWidth, 20), "\ud83e\udde0 RUNTIME ML SELF-LEARNING", headerStyle);
        GUI.Label(new Rect(4 * colWidth, top + 28, colWidth, 20), "\ud83d\udfe2 ONLINE ADAPTATION ACTIVE", learningBadgeStyle);
        GUI.Label(new Rect(4 * colWidth, top + 46, colWidth, 25), "Learning ground truth live...", learningBadgeStyle);

        // Column 6: Camera Mode & Switcher Button
        string modeStr = camCtrl != null ? camCtrl.currentMode.ToString().ToUpper() : "OVERVIEW";
        GUI.Label(new Rect(5 * colWidth, top + 6, colWidth, 18), "\ud83d\udcf7 VIEW: " + modeStr, headerStyle);
        if (GUI.Button(new Rect(5 * colWidth + 15, top + 28, colWidth - 30, 34), "SWITCH VIEW (C)", buttonStyle))
        {
            if (camCtrl != null) camCtrl.CycleCameraMode();
        }
    }
}
