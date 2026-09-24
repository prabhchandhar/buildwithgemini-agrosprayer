# AgroSprayer - Precision Agriculture & Spray Advisory Assistant

![AgroSprayer Demo](demo.gif)

**AgroSprayer** is an AI-powered precision agriculture assistant built on the Google Agent Development Kit (ADK), Vertex AI, and Google Cloud Platform. It provides real-time spray window recommendations, weather analytics, soil monitoring, field management, visual map generation, and video demonstrations for agricultural operations.

---

## 🌾 Implemented Capabilities & Features

Based on the codebase in `app/` and `agents-cli-manifest.yaml`, the agent provides the following fully implemented tools and cloud integrations:

* **🌤️ Live Weather & Delta-T Evaluation (`fetch_live_weather_forecast`)**:
  Fetches real-time weather data from Open-Meteo, calculates Delta-T ($T_{\text{dry}} - T_{\text{wet}}$), monitors wind speeds, and determines whether weather conditions are safe for chemical spraying to prevent spray drift and evaporation.

* **🌱 Soil Condition Monitoring (`fetch_soil_conditions`)**:
  Retrieves current soil moisture levels and temperatures to assess crop field readiness for heavy equipment and chemical absorption.

* **🗄️ Google Cloud Firestore Database (`get_fields`, `add_field`, `log_spray_event`)**:
  Integrated with Google Cloud Firestore to maintain registered farm fields (acreage, crop types, locations) and log historical chemical spraying operations.

* **🗺️ AI Spray Advisory Map Generation (`generate_field_advisory_image`)**:
  Uses **Google Imagen 3** (`imagen-3.0-generate-002`) on Vertex AI to generate custom visual aerial spray advisory maps showing optimal treatment buffer zones and crop boundaries.

* **🎥 Omni Field Operation Video Generation (`generate_field_spray_video`)**:
  Uses **Google Gemini Omni** (`gemini-omni-flash-preview`) in the `global` region to generate short video demonstrations of agricultural field spraying operations.

* **☁️ Public Cloud Storage Media Uploads**:
  Automatically uploads generated images and videos directly to a public Google Cloud Storage (GCS) bucket and returns public HTTPS URLs for seamless inline web viewing.

* **📱 A2UI Protocol & Dynamic UI Cards (`a2ui-agent-sdk`)**:
  Renders interactive A2UI surface component cards (cards, columns, text, images, videos, icons) directly in the user interface.

* **🧠 ADK Memory Bank (`PreloadMemoryTool` & `generate_memories_callback`)**:
  Persists user preferences, farm parameters, and recent field advisories across conversation turns.

---

## 🔮 Planned & Future Enhancements

The following features were outlined in initial design concepts but are not yet implemented in the current code:

* **Tractor IoT Telemetry**: Direct CAN bus integration for real-time sprayer boom pressure and nozzle telemetry streaming *(Planned)*.
* **Autonomous Spray Drones**: Automated flight path generation and payload dispatch for agricultural drones *(Planned)*.

---

## 🛠️ Project Structure

```
agrosprayer/
├── demo.gif                   # Recorded application demo GIF
├── app/                       # Core agent and tools package
│   ├── agent.py               # ADK Root Agent setup & callbacks
│   ├── tools.py               # Weather, Soil, Firestore, Imagen 3 & Omni tools
│   ├── fast_api_app.py        # FastAPI server backend
│   └── app_utils/             # Utility helpers and memory management
├── frontend/                  # Lightweight FastAPI proxy & A2UI Chat Web UI
│   ├── main.py                # Frontend server
│   └── static/index.html      # Responsive Chat UI layout & A2UI renderer
├── pyproject.toml             # Project dependencies and configuration
└── agents-cli-manifest.yaml   # Agents CLI deployment manifest
```

---

## 🚀 Setup & Local Execution Instructions

### Prerequisites

Ensure you have the following tools installed:
* **Python**: `>=3.11`
* **uv**: Python package and environment manager
* **Google Cloud SDK (`gcloud`)**: Configured with your GCP project

### 1. Install Dependencies

Install all required Python packages using `uv`:

```bash
uv sync
```

### 2. Configure Environment Variables

Set your GCP Project ID and GCS Bucket in your environment or `.env` file:

```bash
export FIRESTORE_PROJECT="<your-gcp-project-id>"
export GCS_BUCKET_NAME="<your-gcs-bucket-name>"
```

### 3. Launch Development Playground

Test the agent interactively using the local ADK Playground:

```bash
uv run agents-cli playground
```

### 4. Run the Web Frontend Locally

To run the web interface locally, set your deployed Agent Engine resource name and start the frontend server:

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/us-east1/reasoningEngines/<engine-id>"
export AGENT_DIRECTORY="app"

uv run python -m uvicorn frontend.main:app --host 0.0.0.0 --port 8080
```

---

## ☁️ Deployment

Deploy the agent to Vertex AI Agent Runtime using `agents-cli`:

```bash
uv run agents-cli deploy --no-confirm-project
```

Deploy the web frontend to Google Cloud Run:

```bash
gcloud run deploy agrosprayer-frontend \
  --source ./frontend \
  --region us-central1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<your-agent-engine-resource-name>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
