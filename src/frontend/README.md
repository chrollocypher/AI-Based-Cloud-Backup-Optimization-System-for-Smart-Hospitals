# Backup Console (frontend)

React dashboard for the AI-Based Cloud Backup Optimization System for Smart Hospitals.
It talks to the FastAPI backend in `src/backend` and needs no other services.

## Run it

Start the backend (from `src/backend`):

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Start the frontend (from `src/frontend`):

```bash
npm install
cp .env.example .env      # only needed if the API is not on http://localhost:8000
npm run dev               # http://localhost:5173
```

> On Windows PowerShell, if `npm` is blocked by the execution policy, call `npm.cmd` instead (e.g. `npm.cmd run dev`).

The backend keeps everything in memory, so it is empty after each restart.
Open **Records** and choose **Load sample records** to fill it (same six records as `scripts/seed_data.py`).

## Pages

| Page | What it does | Endpoints |
| --- | --- | --- |
| Overview | Forecast verdict, key figures, workload chart, queue and recent jobs | `GET /dashboard/summary`, `GET /dashboard/workload`, `GET /schedule`, `GET /backups`, `POST /backups`, `POST /schedule` |
| Storage & Retrieval | 7-metric telemetry, retrieval performance, emergency retrieval simulator, retrieval history, S3 cost model, tier transitions, CloudWatch alarms, Step Functions status | `GET /monitoring/system-telemetry`, `GET /monitoring/cloudwatch/alarms`, `GET /storage/cost-estimate`, `POST /storage/tier-transitions`, `POST /retrieval/request`, `POST /retrieval/prefetch`, `GET /retrieval/metrics`, `GET /retrieval/jobs`, `POST /orchestration/trigger-pipeline`, `GET /records` |
| Records | Search, filter, sort, register a record, back up one record | `GET /records`, `GET /records/{id}`, `POST /records`, `POST /backups` |
| Schedule | Capacity gauge and the prioritised queue; regenerate and run | `GET /schedule`, `POST /schedule`, `POST /backups` |
| Backup jobs | Filter by status, fresh job detail, retry | `GET /backups?status=`, `GET /backups/{id}`, `POST /backups/{id}/retry` |
| Forecast | Run and view the backup-volume and access-demand LSTM forecasts, plus the joint intensity directive | `POST /predictions`, `GET /predictions/latest`, `POST /predictions/access-demand`, `GET /predictions/access-demand/latest`, `GET /predictions/joint-forecast`, `POST /schedule` |
| System | Component health, publish CloudWatch metrics, pipeline execution history | `GET /monitoring/status`, `GET /health`, `POST /monitoring/cloudwatch/publish`, `GET /orchestration/executions`, `GET /orchestration/executions/{id}` |

## Configuration

`VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`). The backend already allows any origin through CORS.

## Build

```bash
npm run build              # output in dist/, serve it from a web server
npm run build:standalone   # one self-contained dist-standalone/index.html that opens by double-click
```

The raw `index.html` in this folder is only a template for Vite. Opening it directly shows a blank page; use `npm run dev` or one of the builds above.

## Structure

```
src/
  api/client.js        one function per backend endpoint
  hooks/useApi.js      loading, error and polling state
  components/          Layout, shared UI (tags, panels, drawer, toasts), chart
  pages/               one file per page
  lib/                 formatting helpers and sample data
```
