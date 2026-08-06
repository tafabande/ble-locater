using UnityEngine;
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
            walkCycleTimer += Time.deltaTime * walkSpeed * 8.0f;
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
