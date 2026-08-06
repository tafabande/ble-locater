using UnityEngine;

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
