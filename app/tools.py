import datetime
import json
import urllib.parse
import urllib.request
import uuid
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

# CRITICAL: Always hardcode the exact GCP project ID string as requested.
# Do NOT derive from GOOGLE_CLOUD_PROJECT or google.auth.default() because
# on Agent Platform runtimes, GOOGLE_CLOUD_PROJECT returns the project NUMBER,
# which causes Firestore database resolution errors.
FIRESTORE_PROJECT = "qwiklabs-gcp-02-d5c33db109ac"

# CRITICAL: Hardcode the public Cloud Storage bucket name string
GCS_BUCKET_NAME = "agrosprayer-media-qwiklabs-gcp-02-d5c33db109ac"


def _get_db():
    return firestore.Client(project=FIRESTORE_PROJECT)


def generate_field_advisory_image(
    prompt: str = "Agricultural field spray advisory map diagram with wind speed vector and safe spray zone",
    tool_context: ToolContext = None,
) -> str:
    """Generates an image for agricultural field spraying advisory, saves it to session artifacts,
    and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Description of the field condition, crop spray diagram, or advisory graphic to generate.
        tool_context: ADK context for saving session artifacts.

    Returns:
        Public HTTPS URL of the uploaded image in Cloud Storage.
    """
    try:
        # Use gemini-3.1-flash-lite-image model in global region
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"High quality agricultural visual diagram: {prompt}",
        )

        if not response.candidates or not response.candidates[0].content.parts:
            return "Error: No image content returned from model generation."

        part = response.candidates[0].content.parts[0]
        if not part.inline_data or not part.inline_data.data:
            return "Error: Model response did not contain inline image bytes."

        image_bytes = part.inline_data.data
        mime_type = part.inline_data.mime_type or "image/jpeg"

        filename = f"field_advisory_{uuid.uuid4().hex[:8]}.jpg"

        # (1) Save with tool_context.save_artifact if context is present
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload same image bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating or uploading image: {e}"



def fetch_live_weather_forecast(location: str = "Fresno, CA") -> str:
    """Fetches real live weather data from Open-Meteo and calculates Delta-T spray suitability.

    Args:
        location: City or location name (e.g., 'Fresno, CA', 'Bakersfield', 'Salinas', 'Modesto').

    Returns:
        Real weather conditions, wind speed, relative humidity, calculated Delta-T, and spray safety advice.
    """
    coords = {
        "fresno": (36.7468, -119.7726),
        "bakersfield": (35.3733, -119.0187),
        "salinas": (36.6777, -121.6555),
        "modesto": (37.6393, -120.9970),
        "sacramento": (38.5816, -121.4944),
    }

    loc_lower = location.lower()
    lat, lon = 36.7468, -119.7726
    matched_city = "Fresno, CA"
    for city, (c_lat, c_lon) in coords.items():
        if city in loc_lower:
            lat, lon = c_lat, c_lon
            matched_city = city.title() + ", CA"
            break

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
            f"&wind_speed_unit=mph&temperature_unit=fahrenheit"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "AgroSprayer/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data.get("current", {})
        temp_f = current.get("temperature_2m", 75.0)
        rh = current.get("relative_humidity_2m", 50.0)
        wind_mph = current.get("wind_speed_10m", 5.0)

        # Delta-T calculation approximation (°C)
        temp_c = (temp_f - 32) * 5 / 9
        # Stull's formula for wet bulb temperature approximation
        wet_bulb_c = (
            temp_c * 0.151977 * ((rh + 8.313659) ** 0.5)
            + (temp_c + rh)
            - (rh - 1.676331)
            - 4.686035
        )
        delta_t_c = round(max(0.0, temp_c - wet_bulb_c), 1)

        if delta_t_c < 2.0:
            spray_status = "⚠️ Delta-T is low (<2.0°C). High risk of droplet survival and off-target drift (inversion potential)."
        elif delta_t_c > 10.0:
            spray_status = "⚠️ Delta-T is high (>10.0°C). High risk of droplet evaporation."
        elif wind_mph > 12.0:
            spray_status = f"⚠️ Wind speed ({wind_mph} mph) exceeds safe spray threshold (12.0 mph)."
        else:
            spray_status = "✅ IDEAL spraying conditions. Low evaporation risk and safe wind speed."

        return (
            f"Live weather for {location} ({matched_city}):\n"
            f"• Temperature: {temp_f}°F ({round(temp_c, 1)}°C)\n"
            f"• Relative Humidity: {rh}%\n"
            f"• Wind Speed: {wind_mph} mph\n"
            f"• Calculated Delta-T: {delta_t_c}°C\n"
            f"• Spray Assessment: {spray_status}"
        )
    except Exception as e:
        return f"Error fetching live weather forecast from Open-Meteo for '{location}': {e}"


def fetch_soil_conditions(location: str = "Fresno, CA") -> str:
    """Fetches real-time soil temperature, soil moisture, and trafficability data for farm equipment.

    Args:
        location: City or location name (e.g., 'Fresno, CA', 'Bakersfield', 'Salinas', 'Modesto').

    Returns:
        Real soil temperature, volumetric soil moisture content, and field trafficability assessment.
    """
    import os
    # Read optional API key from environment variable if provided
    api_key = os.environ.get("AGRO_API_KEY", os.environ.get("OPEN_METEO_API_KEY", ""))

    coords = {
        "fresno": (36.7468, -119.7726),
        "bakersfield": (35.3733, -119.0187),
        "salinas": (36.6777, -121.6555),
        "modesto": (37.6393, -120.9970),
        "sacramento": (38.5816, -121.4944),
    }

    loc_lower = location.lower()
    lat, lon = 36.7468, -119.7726
    matched_city = "Fresno, CA"
    for city, (c_lat, c_lon) in coords.items():
        if city in loc_lower:
            lat, lon = c_lat, c_lon
            matched_city = city.title() + ", CA"
            break

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=soil_temperature_0cm,soil_moisture_0_to_1cm"
            f"&temperature_unit=fahrenheit"
        )
        if api_key:
            url += f"&apikey={urllib.parse.quote(api_key)}"

        req = urllib.request.Request(url, headers={"User-Agent": "AgroSprayer/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data.get("current", {})
        soil_temp_f = current.get("soil_temperature_0cm", 75.0)
        soil_moisture = current.get("soil_moisture_0_to_1cm", 0.15)
        moisture_pct = round(soil_moisture * 100, 1)

        # Trafficability assessment for heavy spraying rigs
        if soil_moisture > 0.35:
            trafficability = "⚠️ HIGH MUD RISK: Soil is saturated. High risk of heavy tractor compaction or getting stuck."
        elif soil_moisture < 0.05:
            trafficability = "⚠️ VERY DRY: Dust drift risk. Ensure low nozzle elevation."
        else:
            trafficability = "✅ OPTIMAL TRAFFICABILITY: Soil is firm and dry enough for heavy spray equipment."

        return (
            f"Soil Conditions for {location} ({matched_city}):\n"
            f"• Surface Soil Temperature: {soil_temp_f}°F\n"
            f"• Soil Moisture (0-1cm): {moisture_pct}% ({soil_moisture} m³/m³)\n"
            f"• Field Trafficability: {trafficability}"
        )
    except Exception as e:
        return f"Error fetching soil conditions for '{location}': {e}"



def get_fields(query: str = "") -> str:
    """Lists registered farm fields from the Firestore database.

    Args:
        query: Optional string to filter fields by name, crop type, or location.

    Returns:
        A string list of farm fields and their spraying parameters.
    """
    try:
        db = _get_db()
        docs = db.collection("fields").stream()
        results = []
        q = query.lower().strip()
        for doc in docs:
            data = doc.to_dict()
            if not q or (
                q in data.get("name", "").lower()
                or q in data.get("crop_type", "").lower()
                or q in data.get("location", "").lower()
                or q in data.get("id", "").lower()
            ):
                results.append(data)

        if not results:
            return f"No fields found matching query: '{query}'."

        formatted = []
        for f in results:
            formatted.append(
                f"• [{f.get('id', 'N/A')}] {f.get('name')} | Crop: {f.get('crop_type')} | "
                f"Location: {f.get('location')} | Area: {f.get('acreage')} acres | "
                f"Max Wind: {f.get('max_wind_speed_mph')} mph | Max Temp: {f.get('max_temp_f')}°F | "
                f"Last Sprayed: {f.get('last_sprayed', 'Never')} | Notes: {f.get('notes', '')}"
            )
        return "\n".join(formatted)
    except Exception as e:
        return f"Error retrieving fields from Firestore: {e}"


def add_field(
    field_id: str,
    name: str,
    crop_type: str,
    acreage: float,
    location: str,
    max_wind_speed_mph: float = 10.0,
    max_temp_f: float = 85.0,
    notes: str = "",
) -> str:
    """Adds a new farm field record or updates an existing field in Firestore.

    Args:
        field_id: Unique identifier for the field (e.g., 'field_05').
        name: Human-readable name of the field (e.g., 'East Orchard').
        crop_type: Type of crop planted (e.g., 'Almonds', 'Wheat', 'Corn').
        acreage: Total area of the field in acres.
        location: City or region of the field (e.g., 'Fresno, CA').
        max_wind_speed_mph: Maximum safe wind speed in mph for spraying this field.
        max_temp_f: Maximum safe temperature in Fahrenheit for spraying.
        notes: Optional extra operational notes.

    Returns:
        Confirmation message of the operation.
    """
    try:
        db = _get_db()
        data = {
            "id": field_id,
            "name": name,
            "crop_type": crop_type,
            "acreage": acreage,
            "location": location,
            "max_wind_speed_mph": max_wind_speed_mph,
            "max_temp_f": max_temp_f,
            "last_sprayed": "Never",
            "notes": notes,
        }
        db.collection("fields").document(field_id).set(data)
        return f"Successfully added/updated field '{name}' (ID: {field_id}) in Firestore."
    except Exception as e:
        return f"Error adding field to Firestore: {e}"


def log_spray_event(field_id: str, chemical_used: str, notes: str = "") -> str:
    """Logs a crop spraying event for a specific field in Firestore and updates the last sprayed date.

    Args:
        field_id: The ID of the field that was sprayed (e.g., 'field_01').
        chemical_used: Name of the chemical, fertilizer, or pesticide applied.
        notes: Optional comments about weather or spray outcome.

    Returns:
        Confirmation of the logged spray event.
    """
    try:
        db = _get_db()
        doc_ref = db.collection("fields").document(field_id)
        doc = doc_ref.get()
        if not doc.exists:
            return f"Field ID '{field_id}' not found in Firestore database."

        today_str = datetime.date.today().isoformat()
        field_name = doc.to_dict().get("name", field_id)
        update_data = {
            "last_sprayed": today_str,
            "notes": f"Sprayed {chemical_used} on {today_str}. {notes}".strip(),
        }
        doc_ref.update(update_data)
        return f"Successfully logged spraying event for '{field_name}' (ID: {field_id}) with chemical '{chemical_used}' on {today_str}."
    except Exception as e:
        return f"Error logging spray event in Firestore: {e}"
