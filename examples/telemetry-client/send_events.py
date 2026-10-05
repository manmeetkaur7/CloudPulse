"""Send two example events to CloudPulse's versioned ingestion API."""

import json
import os
from datetime import UTC, datetime
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("CLOUDPULSE_BASE_URL", "http://localhost:8000")
PROJECT_ID = os.environ["CLOUDPULSE_PROJECT_ID"]
SERVICE_ID = os.environ["CLOUDPULSE_SERVICE_ID"]


def send_event(event: dict[str, object]) -> None:
    request = Request(
        f"{BASE_URL}/api/v1/telemetry/events",
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        print(f"accepted event: HTTP {response.status}")


def main() -> None:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    common = {"project_id": PROJECT_ID, "service_id": SERVICE_ID, "timestamp": timestamp, "http_method": "GET", "http_route": "/catalog"}
    send_event({**common, "event_type": "request", "duration_ms": 84, "status_code": 200})
    send_event({**common, "event_type": "error", "status_code": 503, "message": "Example upstream service failure"})


if __name__ == "__main__":
    main()
