"""Seed script for AgroSprayer Firestore database."""
import datetime
from google.cloud import firestore

# CRITICAL: Always hardcode the exact GCP project ID string as requested.
# Do NOT derive from GOOGLE_CLOUD_PROJECT or google.auth.default() because
# on Agent Platform runtimes, GOOGLE_CLOUD_PROJECT returns the project NUMBER,
# which causes Firestore database resolution errors.
FIRESTORE_PROJECT = "qwiklabs-gcp-02-d5c33db109ac"


def seed_database():
    print(f"Connecting to Firestore for project: '{FIRESTORE_PROJECT}'...")
    db = firestore.Client(project=FIRESTORE_PROJECT)

    sample_fields = [
        {
            "id": "field_01",
            "name": "North Barley Field",
            "crop_type": "Barley",
            "acreage": 120.5,
            "location": "Fresno, CA",
            "max_wind_speed_mph": 10.0,
            "ideal_delta_t_min": 2.0,
            "ideal_delta_t_max": 8.0,
            "max_temp_f": 85.0,
            "last_sprayed": "2026-09-10",
            "notes": "Requires herbicide application in early morning",
        },
        {
            "id": "field_02",
            "name": "Valley Corn Field",
            "crop_type": "Corn",
            "acreage": 85.0,
            "location": "Bakersfield, CA",
            "max_wind_speed_mph": 12.0,
            "ideal_delta_t_min": 2.0,
            "ideal_delta_t_max": 10.0,
            "max_temp_f": 90.0,
            "last_sprayed": "2026-09-18",
            "notes": "Monitored for corn borer treatment",
        },
        {
            "id": "field_03",
            "name": "Hilltop Wheat Field",
            "crop_type": "Wheat",
            "acreage": 200.0,
            "location": "Salinas, CA",
            "max_wind_speed_mph": 8.0,
            "ideal_delta_t_min": 1.5,
            "ideal_delta_t_max": 7.5,
            "max_temp_f": 80.0,
            "last_sprayed": "2026-09-01",
            "notes": "High wind risk due to elevation",
        },
        {
            "id": "field_04",
            "name": "Sunset Soybean Acre",
            "crop_type": "Soybean",
            "acreage": 150.0,
            "location": "Modesto, CA",
            "max_wind_speed_mph": 10.0,
            "ideal_delta_t_min": 2.0,
            "ideal_delta_t_max": 8.0,
            "max_temp_f": 88.0,
            "last_sprayed": "2026-09-12",
            "notes": "Fungicide scheduled for next week",
        },
    ]

    collection_ref = db.collection("fields")
    for item in sample_fields:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"Seeded field '{item['id']}': {item['name']} ({item['crop_type']})")

    print("Firestore database seeding complete!")


if __name__ == "__main__":
    seed_database()
