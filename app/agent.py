# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    add_field,
    fetch_live_weather_forecast,
    fetch_soil_conditions,
    generate_field_advisory_image,
    get_fields,
    log_spray_event,
)

MODEL = "gemini-3.8-flash"


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower() or "ca" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        tz_identifier = "America/Los_Angeles"

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


root_agent = Agent(
    # Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
    # from the project `name:` recorded there, and telemetry reports it as
    # gen_ai.agent.name. Renaming the agent only here makes the two disagree,
    # and anything selecting traces by name stops finding this agent's.
    name="agrosprayer",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are AgroSprayer, a precision agriculture assistant. You help farmers check crop field "
        "records in Firestore, fetch live weather, Delta-T, and soil condition forecasts from Open-Meteo, "
        "evaluate weather conditions for optimal spraying windows, log spraying events, generate visual spray advisory diagrams, and manage agricultural field data."
    ),
    tools=[
        fetch_live_weather_forecast,
        fetch_soil_conditions,
        generate_field_advisory_image,
        get_current_time,
        get_fields,
        add_field,
        log_spray_event,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
