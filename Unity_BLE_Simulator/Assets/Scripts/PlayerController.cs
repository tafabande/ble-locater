using UnityEngine;

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
