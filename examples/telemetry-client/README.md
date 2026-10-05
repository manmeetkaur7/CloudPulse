# CloudPulse telemetry client example

This standard-library Python example sends one successful request event and one error event to CloudPulse's real versioned ingestion endpoint.

With the backend running, set identifiers from a project and service you created:

```powershell
$env:CLOUDPULSE_BASE_URL = "http://localhost:8000"
$env:CLOUDPULSE_PROJECT_ID = "your-project-id"
$env:CLOUDPULSE_SERVICE_ID = "your-service-id"
python .\send_events.py
```

The script uses `POST /api/v1/telemetry/events`. It has no external Python dependencies and does not contain credentials.
