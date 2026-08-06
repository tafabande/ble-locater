using UnityEngine;

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
    private Vector3 smoothVelocityLeft;
    private Vector3 smoothVelocityRight;

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
