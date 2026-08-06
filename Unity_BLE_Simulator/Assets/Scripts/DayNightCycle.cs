using UnityEngine;

public class DayNightCycle : MonoBehaviour
{
    [Header("Sun & Atmosphere Controls")]
    public Light sunLight;
    public float dayCycleDurationSeconds = 120f;
    public bool autoRotateSun = true;
    public float timeOfDayNormalized = 0.25f; // 0.25 = 12:00 PM Noon

    [Header("Room Lighting References")]
    public Light[] roomCeilingLights;

    private Color morningSunColor = new Color(1.0f, 0.75f, 0.5f);
    private Color noonSunColor = new Color(1.0f, 0.96f, 0.90f);
    private Color eveningSunColor = new Color(1.0f, 0.5f, 0.25f);
    private Color nightSunColor = new Color(0.15f, 0.2f, 0.35f);

    void Start()
    {
        if (sunLight == null)
        {
            GameObject sunObj = GameObject.Find("Directional Light");
            if (sunObj != null) sunLight = sunObj.GetComponent<Light>();
        }

        if (sunLight != null)
        {
            sunLight.shadows = LightShadows.Soft;
            sunLight.shadowStrength = 0.65f;
        }

        FindRoomLights();
    }

    public void FindRoomLights()
    {
        Light[] allLights = FindObjectsOfType<Light>();
        System.Collections.Generic.List<Light> roomLights = new System.Collections.Generic.List<Light>();
        foreach (var l in allLights)
        {
            if (l.type == LightType.Point || l.type == LightType.Spot)
            {
                if (l.gameObject.name.Contains("Room") || l.gameObject.name.Contains("Ceiling"))
                {
                    roomLights.Add(l);
                }
            }
        }
        roomCeilingLights = roomLights.ToArray();
    }

    void Update()
    {
        if (autoRotateSun)
        {
            timeOfDayNormalized += (Time.deltaTime / dayCycleDurationSeconds);
            if (timeOfDayNormalized > 1.0f) timeOfDayNormalized -= 1.0f;
        }

        float sunAngle = timeOfDayNormalized * 360f - 90f;
        if (sunLight != null)
        {
            sunLight.transform.rotation = Quaternion.Euler(sunAngle, -30f, 0f);

            // Interpolate color and intensity based on sun height
            float sunElevation = Mathf.Sin(timeOfDayNormalized * Mathf.PI * 2f);
            if (sunElevation > 0.3f)
            {
                // Day / Noon
                sunLight.color = Color.Lerp(morningSunColor, noonSunColor, (sunElevation - 0.3f) / 0.7f);
                sunLight.intensity = Mathf.Lerp(0.8f, 1.25f, sunElevation);
            }
            else if (sunElevation > -0.1f)
            {
                // Sunrise / Sunset
                sunLight.color = Color.Lerp(eveningSunColor, morningSunColor, (sunElevation + 0.1f) / 0.4f);
                sunLight.intensity = Mathf.Lerp(0.3f, 0.8f, (sunElevation + 0.1f) / 0.4f);
            }
            else
            {
                // Night
                sunLight.color = nightSunColor;
                sunLight.intensity = 0.15f;
            }
        }

        // Adjust room ceiling lights inversely to outdoor sunlight
        float ceilingIntensity = Mathf.Lerp(1.1f, 0.4f, Mathf.Max(0, Mathf.Sin(timeOfDayNormalized * Mathf.PI * 2f)));
        if (roomCeilingLights != null)
        {
            foreach (var rl in roomCeilingLights)
            {
                if (rl != null) rl.intensity = ceilingIntensity;
            }
        }
    }
}
