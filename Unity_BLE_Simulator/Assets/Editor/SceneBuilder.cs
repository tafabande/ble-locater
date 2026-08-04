#if UNITY_EDITOR
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
