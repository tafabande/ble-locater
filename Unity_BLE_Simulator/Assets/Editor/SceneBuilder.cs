#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public class SceneBuilder : EditorWindow
{
    [MenuItem("BLE Demo/Generate High-Detail 4-Room Complex")]
    public static void GenerateScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        // 1. Room Floor (10m x 10m Facility Complex with Tile Grid Material)
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor_Complex";
        floor.transform.position = new Vector3(5.0f, 0, 5.0f);
        floor.transform.localScale = new Vector3(1.0f, 1, 1.0f);
        Material floorMat = new Material(Shader.Find("Standard"));
        floorMat.color = new Color(0.85f, 0.88f, 0.90f);
        floorMat.SetFloat("_Glossiness", 0.5f);
        floor.GetComponent<Renderer>().sharedMaterial = floorMat;

        // Tag Manager setup
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

        // Palette & Materials
        Material wallMat = new Material(Shader.Find("Standard"));
        wallMat.color = new Color(0.92f, 0.95f, 0.96f);

        Material frameMat = new Material(Shader.Find("Standard"));
        frameMat.color = new Color(0.2f, 0.25f, 0.3f);

        Material windowGlassMat = new Material(Shader.Find("Standard"));
        windowGlassMat.SetFloat("_Mode", 3);
        windowGlassMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        windowGlassMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        windowGlassMat.SetInt("_ZWrite", 0);
        windowGlassMat.EnableKeyword("_ALPHABLEND_ON");
        windowGlassMat.renderQueue = 3000;
        windowGlassMat.color = new Color(0.6f, 0.85f, 0.95f, 0.35f);

        Material doorWoodMat = new Material(Shader.Find("Standard"));
        doorWoodMat.color = new Color(0.55f, 0.35f, 0.2f);

        Material deskFrameMat = new Material(Shader.Find("Standard"));
        deskFrameMat.color = new Color(0.3f, 0.35f, 0.4f);

        Material deskTopMat = new Material(Shader.Find("Standard"));
        deskTopMat.color = new Color(0.2f, 0.5f, 0.8f);

        Material matMat = new Material(Shader.Find("Standard"));
        matMat.color = new Color(0.1f, 0.6f, 0.4f);

        Material woodMat = new Material(Shader.Find("Standard"));
        woodMat.color = new Color(0.6f, 0.4f, 0.25f);

        Material skinToneAlpha = new Material(Shader.Find("Standard"));
        skinToneAlpha.color = new Color(0.22f, 0.14f, 0.08f); 

        Material skinToneBeta = new Material(Shader.Find("Standard"));
        skinToneBeta.color = new Color(0.25f, 0.16f, 0.10f); 

        Material skinToneGamma = new Material(Shader.Find("Standard"));
        skinToneGamma.color = new Color(0.20f, 0.12f, 0.07f); 

        Material hairBlackMat = new Material(Shader.Find("Standard"));
        hairBlackMat.color = new Color(0.08f, 0.06f, 0.05f);

        Material executiveSuitMat = new Material(Shader.Find("Standard"));
        executiveSuitMat.color = new Color(0.95f, 0.95f, 0.98f);

        Material opsLeadMat = new Material(Shader.Find("Standard"));
        opsLeadMat.color = new Color(0.1f, 0.6f, 0.7f);

        Material visitorMat = new Material(Shader.Find("Standard"));
        visitorMat.color = new Color(0.85f, 0.35f, 0.2f); 

        Material trouserDark = new Material(Shader.Find("Standard"));
        trouserDark.color = new Color(0.15f, 0.18f, 0.25f);

        Material shoeBlack = new Material(Shader.Find("Standard"));
        shoeBlack.color = new Color(0.1f, 0.1f, 0.1f);

        Material eyeWhiteMat = new Material(Shader.Find("Standard"));
        eyeWhiteMat.color = Color.white;

        Material eyePupilMat = new Material(Shader.Find("Standard"));
        eyePupilMat.color = Color.black;

        Material sunflowerYellow = new Material(Shader.Find("Standard"));
        sunflowerYellow.color = new Color(1.0f, 0.85f, 0.0f);
        sunflowerYellow.EnableKeyword("_EMISSION");
        sunflowerYellow.SetColor("_EmissionColor", new Color(0.3f, 0.25f, 0.0f));

        Material sunflowerBrown = new Material(Shader.Find("Standard"));
        sunflowerBrown.color = new Color(0.3f, 0.18f, 0.05f);

        Material stemGreen = new Material(Shader.Find("Standard"));
        stemGreen.color = new Color(0.15f, 0.6f, 0.15f);

        Material potMat = new Material(Shader.Find("Standard"));
        potMat.color = new Color(0.7f, 0.35f, 0.2f);

        // 2. Outer Enclosing Boundary Walls + Glass Windows
        BuildWall("Wall_North", new Vector3(5.0f, 1.25f, 10.0f), new Vector3(10.2f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_South", new Vector3(5.0f, 1.25f, 0.0f), new Vector3(10.2f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_West", new Vector3(0.0f, 1.25f, 5.0f), new Vector3(0.2f, 2.5f, 10.2f), wallMat);
        BuildWall("Wall_East", new Vector3(10.0f, 1.25f, 5.0f), new Vector3(0.2f, 2.5f, 10.2f), wallMat);

        BuildWindow("Window_North_RoomA", new Vector3(2.5f, 1.4f, 9.95f), new Vector3(1.6f, 1.0f, 0.08f), windowGlassMat, frameMat);
        BuildWindow("Window_North_RoomB", new Vector3(7.5f, 1.4f, 9.95f), new Vector3(1.6f, 1.0f, 0.08f), windowGlassMat, frameMat);

        // 3. Interior Isolation Dividing Walls with Animated Dual Sliding Automatic Doors & LED Status
        BuildWall("Wall_Div_H_Left", new Vector3(1.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildWall("Wall_Div_H_Right", new Vector3(8.5f, 1.25f, 5.0f), new Vector3(3.0f, 2.5f, 0.2f), wallMat);
        BuildSlidingDoorWithLED("SlidingDoor_RoomA_to_C", new Vector3(4.0f, 1.1f, 5.0f), true, doorWoodMat, frameMat);

        BuildWall("Wall_Div_V_Bottom", new Vector3(5.0f, 1.25f, 1.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildWall("Wall_Div_V_Top", new Vector3(5.0f, 1.25f, 8.5f), new Vector3(0.2f, 2.5f, 3.0f), wallMat);
        BuildSlidingDoorWithLED("SlidingDoor_RoomA_to_B", new Vector3(5.0f, 1.1f, 6.0f), false, doorWoodMat, frameMat);

        // 4. Room Ceiling Lights Setup (4 Rooms)
        BuildRoomCeilingLight("CeilingLight_RoomA", new Vector3(2.5f, 2.3f, 7.5f));
        BuildRoomCeilingLight("CeilingLight_RoomB", new Vector3(7.5f, 2.3f, 7.5f));
        BuildRoomCeilingLight("CeilingLight_RoomC", new Vector3(2.5f, 2.3f, 2.5f));
        BuildRoomCeilingLight("CeilingLight_RoomD", new Vector3(7.5f, 2.3f, 2.5f));

        // 5. 4-Room Workstation & Personnel Setup with Faces & Hair
        BuildDeskWithPersonnel("Desk_RoomA", new Vector3(1.4f, 0, 7.5f), deskFrameMat, deskTopMat, matMat, skinToneAlpha, hairBlackMat, eyeWhiteMat, eyePupilMat, "Personnel Tag (Zone A)");
        CreateSunflowerPot(new Vector3(0.5f, 0, 9.5f), "Sunflower_RoomA", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildDeskWithPersonnel("Desk_RoomB", new Vector3(6.4f, 0, 7.5f), deskFrameMat, deskTopMat, matMat, skinToneBeta, hairBlackMat, eyeWhiteMat, eyePupilMat, "Personnel Tag (Zone B)");
        CreateSunflowerPot(new Vector3(9.5f, 0, 9.5f), "Sunflower_RoomB", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        GameObject deskC = GameObject.CreatePrimitive(PrimitiveType.Cube);
        deskC.name = "Ops_Desk_Room3";
        deskC.tag = "Obstacle";
        deskC.transform.position = new Vector3(8.0f, 0.4f, 2.5f);
        deskC.transform.localScale = new Vector3(1.8f, 0.8f, 0.8f);
        deskC.GetComponent<Renderer>().sharedMaterial = woodMat;
        deskC.AddComponent<DraggableObstacle>();
        CreateSunflowerPot(new Vector3(9.5f, 0, 0.5f), "Sunflower_Room3", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        BuildDeskWithPersonnel("Equipment_Stand_RoomD", new Vector3(8.5f, 0, 2.5f), deskFrameMat, deskTopMat, matMat, skinToneGamma, hairBlackMat, eyeWhiteMat, eyePupilMat, "Equipment Stand (Zone D)");
        CreateSunflowerPot(new Vector3(9.5f, 0, 0.5f), "Sunflower_RoomD", potMat, stemGreen, sunflowerBrown, sunflowerYellow);

        // 6. 12 Beacon Anchors (3 per room) with Dynamic Emitter Glow Lights
        Vector3[] anchorPositions = { 
            new Vector3(0.2f, 0, 5.2f), new Vector3(4.8f, 0, 5.2f), new Vector3(2.5f, 0, 9.8f), // Room A
            new Vector3(5.2f, 0, 5.2f), new Vector3(9.8f, 0, 5.2f), new Vector3(7.5f, 0, 9.8f), // Room B
            new Vector3(0.2f, 0, 0.2f), new Vector3(4.8f, 0, 0.2f), new Vector3(2.5f, 0, 4.8f), // Room C
            new Vector3(5.2f, 0, 0.2f), new Vector3(9.8f, 0, 0.2f), new Vector3(7.5f, 0, 4.8f)  // Room D
        };
        string[] anchorNames = { 
            "ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04", "ANCHOR_05", "ANCHOR_06",
            "ANCHOR_07", "ANCHOR_08", "ANCHOR_09", "ANCHOR_10", "ANCHOR_11", "ANCHOR_12"
        };

        Material pylonMat = new Material(Shader.Find("Standard"));
        pylonMat.color = new Color(0.2f, 0.25f, 0.3f);
        
        Material emitterMat = new Material(Shader.Find("Standard"));
        emitterMat.color = new Color(0f, 0.9f, 0.5f);
        emitterMat.EnableKeyword("_EMISSION");
        emitterMat.SetColor("_EmissionColor", new Color(0f, 0.8f, 0.4f));

        for (int i = 0; i < 12; i++) {
            GameObject anchorRoot = new GameObject(anchorNames[i]);
            anchorRoot.transform.position = anchorPositions[i];

            GameObject pylon = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            pylon.transform.SetParent(anchorRoot.transform);
            pylon.transform.localPosition = new Vector3(0, 0.75f, 0);
            pylon.transform.localScale = new Vector3(0.3f, 0.75f, 0.3f);
            pylon.GetComponent<Renderer>().sharedMaterial = pylonMat;

            GameObject emitter = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            emitter.transform.SetParent(anchorRoot.transform);
            emitter.transform.localPosition = new Vector3(0, 1.6f, 0);
            emitter.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);
            emitter.GetComponent<Renderer>().sharedMaterial = emitterMat;

            GameObject beaconLightObj = new GameObject("BeaconGlowLight");
            beaconLightObj.transform.SetParent(emitter.transform);
            beaconLightObj.transform.localPosition = Vector3.zero;
            Light bl = beaconLightObj.AddComponent<Light>();
            bl.type = LightType.Point;
            bl.color = new Color(0f, 0.9f, 0.6f);
            bl.intensity = 0.8f;
            bl.range = 3.5f;

            GameObject labelObj = new GameObject("Label");
            labelObj.transform.SetParent(anchorRoot.transform);
            labelObj.transform.localPosition = new Vector3(0, 2.2f, 0);
            TextMesh tm = labelObj.AddComponent<TextMesh>();
            tm.text = anchorNames[i] + string.Format("
({0:F1}, {1:F1})", anchorPositions[i].x, anchorPositions[i].z);
            tm.fontSize = 22;
            tm.characterSize = 0.07f;
            tm.color = Color.cyan;
            tm.alignment = TextAlignment.Center;
            tm.anchor = TextAnchor.MiddleCenter;
        }

        // 7. Detailed 3D Humanoid Entities (Legs, Arms, Hair, Face Features & Walking Animation)
        CreateRealisticHumanoid("User_Alpha", new Vector3(2.5f, 0.9f, 2.5f), executiveSuitMat, trouserDark, skinToneAlpha, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(2.5f, 0.9f, 2.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(7.5f, 0.9f, 2.5f)
        }, "\ud83d\udc68\u200d\ud83d\udcbc User Alpha (Consultant)", true, false);

        CreateRealisticHumanoid("User_Beta", new Vector3(7.5f, 0.9f, 2.5f), opsLeadMat, opsLeadMat, skinToneBeta, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(7.5f, 0.9f, 2.5f), new Vector3(7.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 7.5f), new Vector3(2.5f, 0.9f, 2.5f)
        }, "\ud83d\udc69\u200d\ud83d\udcbc User Beta (Operations Lead)", false, true);

        CreateRealisticHumanoid("Visitor_Gamma", new Vector3(6.5f, 0.9f, 6.5f), visitorMat, trouserDark, skinToneGamma, hairBlackMat, eyeWhiteMat, eyePupilMat, shoeBlack, new Vector3[] {
            new Vector3(6.5f, 0.9f, 6.5f), new Vector3(3.0f, 0.9f, 3.0f), new Vector3(8.0f, 0.9f, 3.0f), new Vector3(6.5f, 0.9f, 6.5f)
        }, "\ud83c\udfc3 Visitor Gamma", false, false);

        // 8. Smartphone Tag Device (True Tag)
        GameObject trueTag = new GameObject("True_Tag (Drag Me)");
        trueTag.transform.position = new Vector3(2.5f, 0.4f, 7.5f);
        BoxCollider tagCol = trueTag.AddComponent<BoxCollider>();
        tagCol.size = new Vector3(0.6f, 0.4f, 0.8f);

        GameObject phoneBody = GameObject.CreatePrimitive(PrimitiveType.Cube);
        phoneBody.name = "PhoneBody";
        phoneBody.transform.SetParent(trueTag.transform);
        phoneBody.transform.localPosition = Vector3.zero;
        phoneBody.transform.localScale = new Vector3(0.35f, 0.06f, 0.65f);
        Material bodyMat = new Material(Shader.Find("Standard"));
        bodyMat.color = new Color(0.1f, 0.1f, 0.12f);
        phoneBody.GetComponent<Renderer>().sharedMaterial = bodyMat;

        GameObject phoneScreen = GameObject.CreatePrimitive(PrimitiveType.Quad);
        phoneScreen.name = "PhoneScreen";
        phoneScreen.transform.SetParent(trueTag.transform);
        phoneScreen.transform.localPosition = new Vector3(0, 0.035f, 0);
        phoneScreen.transform.localRotation = Quaternion.Euler(90f, 0, 0);
        phoneScreen.transform.localScale = new Vector3(0.3f, 0.58f, 1f);
        Material phoneScreenMat = new Material(Shader.Find("Standard"));
        phoneScreenMat.color = new Color(0.9f, 0.1f, 0.1f);
        phoneScreenMat.EnableKeyword("_EMISSION");
        phoneScreenMat.SetColor("_EmissionColor", new Color(0.8f, 0.1f, 0.1f));
        phoneScreen.GetComponent<Renderer>().sharedMaterial = phoneScreenMat;

        GameObject trueHudObj = new GameObject("HUD");
        trueHudObj.transform.SetParent(trueTag.transform);
        trueHudObj.transform.localPosition = new Vector3(0, 1.2f, 0);
        TextMesh trueTm = trueHudObj.AddComponent<TextMesh>();
        trueTm.fontSize = 24;
        trueTm.characterSize = 0.07f;
        trueTm.color = new Color(1f, 0.4f, 0.4f);
        trueTm.alignment = TextAlignment.Center;
        trueTm.anchor = TextAnchor.MiddleCenter;

        trueTag.AddComponent<PlayerController>();
        BLESimulator sim = trueTag.AddComponent<BLESimulator>();
        sim.hudText = trueTm;

        // 9. Predicted Holographic Tag Device (Ghost Tag)
        GameObject ghostTag = new GameObject("Ghost_Tag (Predicted)");
        ghostTag.transform.position = new Vector3(2.5f, 0.4f, 7.5f);

        GameObject ghostBody = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ghostBody.name = "GhostBody";
        ghostBody.transform.SetParent(ghostTag.transform);
        ghostBody.transform.localPosition = Vector3.zero;
        ghostBody.transform.localScale = new Vector3(0.4f, 0.08f, 0.7f);
        ghostBody.GetComponent<Collider>().enabled = false;

        Material ghostMat = new Material(Shader.Find("Standard"));
        ghostMat.SetFloat("_Mode", 3);
        ghostMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
        ghostMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
        ghostMat.SetInt("_ZWrite", 0);
        ghostMat.EnableKeyword("_ALPHABLEND_ON");
        ghostMat.renderQueue = 3000;
        ghostMat.color = new Color(0f, 0.7f, 1f, 0.6f);
        ghostMat.EnableKeyword("_EMISSION");
        ghostMat.SetColor("_EmissionColor", new Color(0f, 0.5f, 1f));
        ghostBody.GetComponent<Renderer>().sharedMaterial = ghostMat;

        TrailRenderer trail = ghostTag.AddComponent<TrailRenderer>();
        trail.time = 4.0f;
        trail.startWidth = 0.15f;
        trail.endWidth = 0.02f;
        trail.material = new Material(Shader.Find("Sprites/Default"));
        trail.startColor = new Color(0f, 0.8f, 1f, 0.8f);
        trail.endColor = new Color(0f, 0.2f, 1f, 0.0f);

        GameObject ghostHudObj = new GameObject("HUD");
        ghostHudObj.transform.SetParent(ghostTag.transform);
        ghostHudObj.transform.localPosition = new Vector3(0, 1.6f, 0);
        TextMesh ghostTm = ghostHudObj.AddComponent<TextMesh>();
        ghostTm.fontSize = 24;
        ghostTm.characterSize = 0.07f;
        ghostTm.color = new Color(0.3f, 0.8f, 1f);
        ghostTm.alignment = TextAlignment.Center;
        ghostTm.anchor = TextAnchor.MiddleCenter;

        TagVisualizer vis = ghostTag.AddComponent<TagVisualizer>();
        vis.hudText = ghostTm;

        // 10. Attach Bottom Live Telemetry Table HUD
        GameObject tableManager = new GameObject("HUDTableManager");
        tableManager.AddComponent<HUDTableUI>();

        // 11. Camera & Dynamic Lighting Controller Setup
        Camera.main.transform.position = new Vector3(5.0f, 11.5f, -2.5f);
        Camera.main.transform.rotation = Quaternion.Euler(60f, 0f, 0f);
        Camera.main.backgroundColor = new Color(0.88f, 0.92f, 0.95f);
        if (Camera.main.GetComponent<CameraController>() == null) {
            CameraController cc = Camera.main.gameObject.AddComponent<CameraController>();
            cc.targetPlayer = trueTag.transform;
        }

        GameObject lightObj = GameObject.Find("Directional Light");
        if (lightObj == null) {
            lightObj = new GameObject("Directional Light");
            Light l = lightObj.AddComponent<Light>();
            l.type = LightType.Directional;
        }
        lightObj.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
        Light mainSun = lightObj.GetComponent<Light>();
        mainSun.shadows = LightShadows.Soft;

        if (lightObj.GetComponent<DayNightCycle>() == null) {
            lightObj.AddComponent<DayNightCycle>();
        }

        Debug.Log("Successfully generated High-Detail 4-Room Complex with Realistic 3D People, Smooth LED Doors & Dynamic Lighting!");
    }

    private static void BuildWall(string name, Vector3 pos, Vector3 scale, Material mat)
    {
        GameObject wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall.name = name;
        wall.tag = "Obstacle";
        wall.transform.position = pos;
        wall.transform.localScale = scale;
        wall.GetComponent<Renderer>().sharedMaterial = mat;
    }

    private static void BuildWindow(string name, Vector3 pos, Vector3 scale, Material glassMat, Material frameMat)
    {
        GameObject winRoot = new GameObject(name);
        winRoot.transform.position = pos;

        GameObject glass = GameObject.CreatePrimitive(PrimitiveType.Cube);
        glass.name = "GlassPane";
        glass.transform.SetParent(winRoot.transform);
        glass.transform.localPosition = Vector3.zero;
        glass.transform.localScale = scale;
        glass.GetComponent<Renderer>().sharedMaterial = glassMat;

        GameObject frame = GameObject.CreatePrimitive(PrimitiveType.Cube);
        frame.name = "WindowFrame";
        frame.transform.SetParent(winRoot.transform);
        frame.transform.localPosition = Vector3.zero;
        frame.transform.localScale = new Vector3(scale.x + 0.1f, scale.y + 0.1f, 0.04f);
        frame.GetComponent<Renderer>().sharedMaterial = frameMat;
    }

    private static void BuildRoomCeilingLight(string name, Vector3 pos)
    {
        GameObject lightRoot = new GameObject(name);
        lightRoot.transform.position = pos;

        GameObject fixture = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        fixture.transform.SetParent(lightRoot.transform);
        fixture.transform.localPosition = Vector3.zero;
        fixture.transform.localScale = new Vector3(0.5f, 0.05f, 0.5f);
        Material fixMat = new Material(Shader.Find("Standard"));
        fixMat.color = new Color(0.9f, 0.95f, 1.0f);
        fixMat.EnableKeyword("_EMISSION");
        fixMat.SetColor("_EmissionColor", new Color(0.8f, 0.85f, 0.9f));
        fixture.GetComponent<Renderer>().sharedMaterial = fixMat;

        Light pointL = lightRoot.AddComponent<Light>();
        pointL.type = LightType.Point;
        pointL.color = new Color(0.95f, 0.95f, 1.0f);
        pointL.intensity = 0.9f;
        pointL.range = 8.0f;
        pointL.shadows = LightShadows.Soft;
    }

    private static void BuildSlidingDoorWithLED(string name, Vector3 pos, bool isHorizontal, Material doorMat, Material frameMat)
    {
        GameObject doorRoot = new GameObject(name);
        doorRoot.tag = "Obstacle";
        doorRoot.transform.position = pos;

        BoxCollider mainCol = doorRoot.AddComponent<BoxCollider>();
        mainCol.size = isHorizontal ? new Vector3(1.8f, 2.2f, 0.3f) : new Vector3(0.3f, 2.2f, 1.8f);

        GameObject track = GameObject.CreatePrimitive(PrimitiveType.Cube);
        track.name = "DoorTrackFrame";
        track.transform.SetParent(doorRoot.transform);
        track.transform.localPosition = new Vector3(0, 1.15f, 0);
        track.transform.localScale = isHorizontal ? new Vector3(1.9f, 0.12f, 0.2f) : new Vector3(0.2f, 0.12f, 1.9f);
        track.GetComponent<Renderer>().sharedMaterial = frameMat;

        GameObject led = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        led.name = "StatusLED";
        led.transform.SetParent(doorRoot.transform);
        led.transform.localPosition = new Vector3(0, 1.25f, 0);
        led.transform.localScale = new Vector3(0.12f, 0.12f, 0.12f);
        Material ledMat = new Material(Shader.Find("Standard"));
        ledMat.color = new Color(1f, 0.1f, 0.1f);
        ledMat.EnableKeyword("_EMISSION");
        ledMat.SetColor("_EmissionColor", new Color(1f, 0.1f, 0.1f));
        led.GetComponent<Renderer>().sharedMaterial = ledMat;

        Light ledLight = led.AddComponent<Light>();
        ledLight.type = LightType.Point;
        ledLight.color = new Color(1f, 0.1f, 0.1f);
        ledLight.intensity = 0.6f;
        ledLight.range = 1.5f;

        GameObject leftLeaf = GameObject.CreatePrimitive(PrimitiveType.Cube);
        leftLeaf.name = "LeftLeaf";
        leftLeaf.transform.SetParent(doorRoot.transform);
        leftLeaf.transform.localPosition = isHorizontal ? new Vector3(-0.42f, 0, 0) : new Vector3(0, 0, -0.42f);
        leftLeaf.transform.localScale = isHorizontal ? new Vector3(0.85f, 2.1f, 0.08f) : new Vector3(0.08f, 2.1f, 0.85f);
        leftLeaf.GetComponent<Renderer>().sharedMaterial = doorMat;

        GameObject rightLeaf = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rightLeaf.name = "RightLeaf";
        rightLeaf.transform.SetParent(doorRoot.transform);
        rightLeaf.transform.localPosition = isHorizontal ? new Vector3(0.42f, 0, 0) : new Vector3(0, 0, 0.42f);
        rightLeaf.transform.localScale = isHorizontal ? new Vector3(0.85f, 2.1f, 0.08f) : new Vector3(0.08f, 2.1f, 0.85f);
        rightLeaf.GetComponent<Renderer>().sharedMaterial = doorMat;

        DoorController controller = doorRoot.AddComponent<DoorController>();
        controller.leftPanel = leftLeaf.transform;
        controller.rightPanel = rightLeaf.transform;
        controller.statusLedLight = ledLight;
        controller.statusLedRenderer = led.GetComponent<Renderer>();
    }

    private static void BuildDeskWithPersonnel(string name, Vector3 pos, Material frameMat, Material matMat, Material blanketMat, Material skinMat, Material hairMat, Material eyeWhiteMat, Material eyePupilMat, string personnelName)
    {
        GameObject desk = new GameObject(name);
        desk.transform.position = pos;

        GameObject deskTop = GameObject.CreatePrimitive(PrimitiveType.Cube);
        deskTop.name = "Desk_Obstacle";
        deskTop.tag = "Obstacle";
        deskTop.transform.SetParent(desk.transform);
        deskTop.transform.localPosition = new Vector3(0, 0.45f, 0);
        deskTop.transform.localScale = new Vector3(1.2f, 0.35f, 2.1f);
        deskTop.GetComponent<Renderer>().sharedMaterial = matMat;

        GameObject monitor = GameObject.CreatePrimitive(PrimitiveType.Cube);
        monitor.name = "Monitor";
        monitor.transform.SetParent(desk.transform);
        monitor.transform.localPosition = new Vector3(0, 0.65f, 0.7f);
        monitor.transform.localScale = new Vector3(0.8f, 0.12f, 0.45f);

        GameObject pad = GameObject.CreatePrimitive(PrimitiveType.Cube);
        pad.name = "DeskPad";
        pad.transform.SetParent(desk.transform);
        pad.transform.localPosition = new Vector3(0, 0.65f, -0.2f);
        pad.transform.localScale = new Vector3(1.15f, 0.15f, 1.4f);
        pad.GetComponent<Renderer>().sharedMaterial = blanketMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "TagNodeHead";
        head.transform.SetParent(desk.transform);
        head.transform.localPosition = new Vector3(0, 0.75f, 0.7f);
        head.transform.localScale = new Vector3(0.35f, 0.35f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        BuildFaceFeatures(head.transform, eyeWhiteMat, eyePupilMat, skinMat, hairMat);

        GameObject leftArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        leftArm.transform.SetParent(desk.transform);
        leftArm.transform.localPosition = new Vector3(-0.45f, 0.72f, 0.2f);
        leftArm.transform.localRotation = Quaternion.Euler(0, 0, 10f);
        leftArm.transform.localScale = new Vector3(0.08f, 0.35f, 0.08f);
        leftArm.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject rightArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rightArm.transform.SetParent(desk.transform);
        rightArm.transform.localPosition = new Vector3(0.45f, 0.72f, 0.2f);
        rightArm.transform.localRotation = Quaternion.Euler(0, 0, -10f);
        rightArm.transform.localScale = new Vector3(0.08f, 0.35f, 0.08f);
        rightArm.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(desk.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.3f, 0.7f);
        TextMesh tm = labelObj.AddComponent<TextMesh>();
        tm.text = "\ud83d\udcbb " + personnelName;
        tm.fontSize = 20;
        tm.characterSize = 0.06f;
        tm.color = Color.white;
        tm.alignment = TextAlignment.Center;
        tm.anchor = TextAnchor.MiddleCenter;
    }

    private static void CreateRealisticHumanoid(string name, Vector3 pos, Material outfitMat, Material trouserMat, Material skinMat, Material hairMat, Material eyeWhiteMat, Material eyePupilMat, Material shoeMat, Vector3[] waypoints, string label, bool isConsultant, bool isLead)
    {
        GameObject human = new GameObject(name);
        human.tag = "Obstacle";
        human.transform.position = pos;

        GameObject chest = GameObject.CreatePrimitive(PrimitiveType.Cube);
        chest.name = "ChestTorso";
        chest.transform.SetParent(human.transform);
        chest.transform.localPosition = new Vector3(0, 0.95f, 0);
        chest.transform.localScale = new Vector3(0.45f, 0.55f, 0.26f);
        chest.GetComponent<Renderer>().sharedMaterial = outfitMat;

        if (isConsultant)
        {
            GameObject badge = GameObject.CreatePrimitive(PrimitiveType.Cube);
            badge.name = "ID_Badge";
            badge.transform.SetParent(chest.transform);
            badge.transform.localPosition = new Vector3(0.12f, 0.1f, 0.52f);
            badge.transform.localScale = new Vector3(0.15f, 0.22f, 0.04f);
            Material badgeMat = new Material(Shader.Find("Standard"));
            badgeMat.color = Color.cyan;
            badge.GetComponent<Renderer>().sharedMaterial = badgeMat;
        }

        GameObject neck = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        neck.name = "Neck";
        neck.transform.SetParent(human.transform);
        neck.transform.localPosition = new Vector3(0, 1.26f, 0);
        neck.transform.localScale = new Vector3(0.12f, 0.08f, 0.12f);
        neck.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "MelaninHeadMesh";
        head.transform.SetParent(human.transform);
        head.transform.localPosition = new Vector3(0, 1.45f, 0);
        head.transform.localScale = new Vector3(0.35f, 0.35f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = skinMat;

        BuildFaceFeatures(head.transform, eyeWhiteMat, eyePupilMat, skinMat, hairMat);

        GameObject leftArmPivot = new GameObject("LeftArm");
        leftArmPivot.transform.SetParent(human.transform);
        leftArmPivot.transform.localPosition = new Vector3(-0.28f, 1.15f, 0);

        GameObject lUpperArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        lUpperArm.transform.SetParent(leftArmPivot.transform);
        lUpperArm.transform.localPosition = new Vector3(0, -0.16f, 0);
        lUpperArm.transform.localScale = new Vector3(0.1f, 0.16f, 0.1f);
        lUpperArm.GetComponent<Renderer>().sharedMaterial = outfitMat;

        GameObject lHand = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lHand.transform.SetParent(leftArmPivot.transform);
        lHand.transform.localPosition = new Vector3(0, -0.34f, 0);
        lHand.transform.localScale = new Vector3(0.11f, 0.11f, 0.11f);
        lHand.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject rightArmPivot = new GameObject("RightArm");
        rightArmPivot.transform.SetParent(human.transform);
        rightArmPivot.transform.localPosition = new Vector3(0.28f, 1.15f, 0);

        GameObject rUpperArm = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rUpperArm.transform.SetParent(rightArmPivot.transform);
        rUpperArm.transform.localPosition = new Vector3(0, -0.16f, 0);
        rUpperArm.transform.localScale = new Vector3(0.1f, 0.16f, 0.1f);
        rUpperArm.GetComponent<Renderer>().sharedMaterial = outfitMat;

        GameObject rHand = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rHand.transform.SetParent(rightArmPivot.transform);
        rHand.transform.localPosition = new Vector3(0, -0.34f, 0);
        rHand.transform.localScale = new Vector3(0.11f, 0.11f, 0.11f);
        rHand.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject leftLegPivot = new GameObject("LeftLeg");
        leftLegPivot.transform.SetParent(human.transform);
        leftLegPivot.transform.localPosition = new Vector3(-0.13f, 0.68f, 0);

        GameObject lThigh = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        lThigh.transform.SetParent(leftLegPivot.transform);
        lThigh.transform.localPosition = new Vector3(0, -0.3f, 0);
        lThigh.transform.localScale = new Vector3(0.13f, 0.3f, 0.13f);
        lThigh.GetComponent<Renderer>().sharedMaterial = trouserMat;

        GameObject lShoe = GameObject.CreatePrimitive(PrimitiveType.Cube);
        lShoe.transform.SetParent(leftLegPivot.transform);
        lShoe.transform.localPosition = new Vector3(0, -0.62f, 0.05f);
        lShoe.transform.localScale = new Vector3(0.14f, 0.08f, 0.22f);
        lShoe.GetComponent<Renderer>().sharedMaterial = shoeMat;

        GameObject rightLegPivot = new GameObject("RightLeg");
        rightLegPivot.transform.SetParent(human.transform);
        rightLegPivot.transform.localPosition = new Vector3(0.13f, 0.68f, 0);

        GameObject rThigh = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        rThigh.transform.SetParent(rightLegPivot.transform);
        rThigh.transform.localPosition = new Vector3(0, -0.3f, 0);
        rThigh.transform.localScale = new Vector3(0.13f, 0.3f, 0.13f);
        rThigh.GetComponent<Renderer>().sharedMaterial = trouserMat;

        GameObject rShoe = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rShoe.transform.SetParent(rightLegPivot.transform);
        rShoe.transform.localPosition = new Vector3(0, -0.62f, 0.05f);
        rShoe.transform.localScale = new Vector3(0.14f, 0.08f, 0.22f);
        rShoe.GetComponent<Renderer>().sharedMaterial = shoeMat;

        GameObject labelObj = new GameObject("Label");
        labelObj.transform.SetParent(human.transform);
        labelObj.transform.localPosition = new Vector3(0, 1.85f, 0);
        TextMesh tm = labelObj.AddComponent<TextMesh>();
        tm.text = label;
        tm.fontSize = 22;
        tm.characterSize = 0.06f;
        tm.color = new Color(0.2f, 0.2f, 0.8f);
        tm.alignment = TextAlignment.Center;
        tm.anchor = TextAnchor.MiddleCenter;

        HumanWalker walker = human.AddComponent<HumanWalker>();
        walker.waypoints = waypoints;
        walker.labelText = tm;
        walker.leftLeg = leftLegPivot.transform;
        walker.rightLeg = rightLegPivot.transform;
        walker.leftArm = leftArmPivot.transform;
        walker.rightArm = rightArmPivot.transform;
        walker.headMesh = head.transform;
    }

    private static void BuildFaceFeatures(Transform headTransform, Material eyeWhiteMat, Material eyePupilMat, Material skinMat, Material hairMat)
    {
        GameObject lEyeWhite = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lEyeWhite.name = "LeftEyeWhite";
        lEyeWhite.transform.SetParent(headTransform);
        lEyeWhite.transform.localPosition = new Vector3(-0.16f, 0.08f, 0.42f);
        lEyeWhite.transform.localScale = new Vector3(0.18f, 0.18f, 0.12f);
        lEyeWhite.GetComponent<Renderer>().sharedMaterial = eyeWhiteMat;

        GameObject lPupil = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        lPupil.name = "LeftPupil";
        lPupil.transform.SetParent(lEyeWhite.transform);
        lPupil.transform.localPosition = new Vector3(0, 0, 0.45f);
        lPupil.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f);
        lPupil.GetComponent<Renderer>().sharedMaterial = eyePupilMat;

        GameObject rEyeWhite = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rEyeWhite.name = "RightEyeWhite";
        rEyeWhite.transform.SetParent(headTransform);
        rEyeWhite.transform.localPosition = new Vector3(0.16f, 0.08f, 0.42f);
        rEyeWhite.transform.localScale = new Vector3(0.18f, 0.18f, 0.12f);
        rEyeWhite.GetComponent<Renderer>().sharedMaterial = eyeWhiteMat;

        GameObject rPupil = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rPupil.name = "RightPupil";
        rPupil.transform.SetParent(rEyeWhite.transform);
        rPupil.transform.localPosition = new Vector3(0, 0, 0.45f);
        rPupil.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f);
        rPupil.GetComponent<Renderer>().sharedMaterial = eyePupilMat;

        GameObject lBrow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        lBrow.transform.SetParent(headTransform);
        lBrow.transform.localPosition = new Vector3(-0.16f, 0.22f, 0.42f);
        lBrow.transform.localScale = new Vector3(0.22f, 0.04f, 0.06f);
        lBrow.GetComponent<Renderer>().sharedMaterial = hairMat;

        GameObject rBrow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        rBrow.transform.SetParent(headTransform);
        rBrow.transform.localPosition = new Vector3(0.16f, 0.22f, 0.42f);
        rBrow.transform.localScale = new Vector3(0.22f, 0.04f, 0.06f);
        rBrow.GetComponent<Renderer>().sharedMaterial = hairMat;

        GameObject nose = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nose.name = "Nose";
        nose.transform.SetParent(headTransform);
        nose.transform.localPosition = new Vector3(0, -0.04f, 0.48f);
        nose.transform.localScale = new Vector3(0.1f, 0.14f, 0.12f);
        nose.GetComponent<Renderer>().sharedMaterial = skinMat;

        GameObject mouth = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mouth.name = "Lips";
        mouth.transform.SetParent(headTransform);
        mouth.transform.localPosition = new Vector3(0, -0.22f, 0.44f);
        mouth.transform.localScale = new Vector3(0.22f, 0.06f, 0.06f);
        Material lipMat = new Material(Shader.Find("Standard"));
        lipMat.color = new Color(0.35f, 0.18f, 0.15f);
        mouth.GetComponent<Renderer>().sharedMaterial = lipMat;

        GameObject hairCluster = new GameObject("HairMeshCluster");
        hairCluster.transform.SetParent(headTransform);
        hairCluster.transform.localPosition = Vector3.zero;

        Vector3[] hairOffsets = {
            new Vector3(0, 0.28f, -0.05f), new Vector3(-0.18f, 0.24f, 0), new Vector3(0.18f, 0.24f, 0),
            new Vector3(0, 0.26f, 0.15f), new Vector3(-0.12f, 0.26f, -0.16f), new Vector3(0.12f, 0.26f, -0.16f)
        };
        foreach (var offset in hairOffsets)
        {
            GameObject puff = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            puff.transform.SetParent(hairCluster.transform);
            puff.transform.localPosition = offset;
            puff.transform.localScale = new Vector3(0.55f, 0.55f, 0.55f);
            puff.GetComponent<Renderer>().sharedMaterial = hairMat;
        }
    }

    private static void CreateSunflowerPot(Vector3 pos, string name, Material potMat, Material stemMat, Material centerMat, Material petalMat)
    {
        GameObject plantRoot = new GameObject(name);
        plantRoot.transform.position = pos;

        GameObject pot = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        pot.transform.SetParent(plantRoot.transform);
        pot.transform.localPosition = new Vector3(0, 0.2f, 0);
        pot.transform.localScale = new Vector3(0.35f, 0.2f, 0.35f);
        pot.GetComponent<Renderer>().sharedMaterial = potMat;

        GameObject stem = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        stem.transform.SetParent(plantRoot.transform);
        stem.transform.localPosition = new Vector3(0, 0.65f, 0);
        stem.transform.localScale = new Vector3(0.04f, 0.3f, 0.04f);
        stem.GetComponent<Renderer>().sharedMaterial = stemMat;

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        head.transform.SetParent(plantRoot.transform);
        head.transform.localPosition = new Vector3(0, 1.0f, 0);
        head.transform.localRotation = Quaternion.Euler(30f, 0, 0);
        head.transform.localScale = new Vector3(0.35f, 0.02f, 0.35f);
        head.GetComponent<Renderer>().sharedMaterial = centerMat;

        for (int i = 0; i < 8; i++) {
            float angle = i * 45f * Mathf.Deg2Rad;
            GameObject petal = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            petal.transform.SetParent(head.transform);
            petal.transform.localPosition = new Vector3(Mathf.Cos(angle) * 0.2f, 0, Mathf.Sin(angle) * 0.2f);
            petal.transform.localScale = new Vector3(0.12f, 0.06f, 0.12f);
            petal.GetComponent<Renderer>().sharedMaterial = petalMat;
        }
    }
}
#endif
