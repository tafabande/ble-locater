using UnityEngine;

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
