# Financial Data Preprocessor

A local web application for cleaning and analyzing financial datasets. The
frontend and backend live in separate folders and communicate through a JSON
HTTP API.

## Project structure

```text
backend/
  app/
    api/       FastAPI routes
    core/      Application configuration and shared settings
    models/    API request and response models
    services/  File processing and financial analysis logic
    main.py    FastAPI app, CORS, and route registration
  tests/       Backend tests
  requirements.txt       Runtime Python packages
  requirements-dev.txt   Test and lint tools
frontend/
  src/
    services/  Calls from React to the API
    dashboard/ Dashboard sections, data table, and analysis charts
    App.jsx    Landing page and entry point to the dashboard
    main.jsx   React application entry point
  index.html   Browser page metadata and React mount point
  vite.config.js  Frontend development server and API proxy
```

## Requirements

- Node.js 20.19+ (or 22.12+)
- Python 3.10+

## Run locally (PowerShell)

In the project root, prepare the backend environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

The API runs at http://127.0.0.1:8000. Interactive API docs are at
http://127.0.0.1:8000/docs, and the test endpoint is
http://127.0.0.1:8000/api/health.

The dashboard accepts CSV and `.xlsx` uploads up to 20 MB. It detects common
date, amount, transaction-type, and category columns by their names. Income and
expense totals use recognized transaction labels when available, otherwise
positive values count as income and negative values as expenses. Uploaded data
is held temporarily in backend memory; restarting FastAPI clears it.

Main dataset API routes are `POST /api/datasets` (upload),
`POST /api/datasets/{id}/clean/preview` (preview without applying),
`POST /api/datasets/{id}/clean` (apply from the original upload),
`POST /api/datasets/{id}/undo`, `POST /api/datasets/{id}/reset`,
`GET /api/datasets/{id}/validation`, `GET /api/datasets/{id}/analysis`,
`GET /api/datasets/{id}/quality`, `GET /api/datasets/{id}/quality/pdf`
(visual PDF report), and `GET /api/datasets/{id}/export?format=csv` or
`format=xlsx`.

The visual quality PDF is generated from the same quality report data as the
JSON download. It includes financial summary cards, income and expense charts,
category summaries, data quality findings, cleaning status, and recommendations.
Missing financial values are labelled as unavailable rather than treated as
zero. The PDF generator uses ReportLab and an embedded Unicode font to render
Indian Rupee amounts correctly; these dependencies are included in
`backend/requirements.txt` and the production Docker image.

## Deploy publicly on Render

This folder includes a Render Blueprint at `Financial_Data_Preprocessor/render.yaml`
and a multi-stage `Dockerfile`. Render builds the Vite frontend and serves it
from FastAPI, so the browser uses the same-origin `/api` path in production.
The normal local Vite proxy remains in place for development. `CORS_ORIGINS`
is an optional comma-separated setting for a separately hosted frontend; it is
not required for the single-service deployment. See `.env.example` for notes.

To deploy, connect the GitHub repository containing this folder to Render and
create a Blueprint using the Blueprint path
`Financial_Data_Preprocessor/render.yaml`. The Blueprint sets the service root
to this folder and uses `/api/health` for health checks. Render assigns the
public `onrender.com` address after the first successful deploy.

Uploaded datasets are held in process memory, not stored permanently. They are
lost when the service restarts or sleeps, and a dataset is not shared between
separate service instances. The configured free web service may sleep while
idle, so the first request after inactivity can take longer while it wakes.

In a second terminal, install and run the frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally http://127.0.0.1:5173). Requests under
`/api` are forwarded to FastAPI by the Vite development proxy.

## Verify

From the project root, with the backend development dependencies installed:

```powershell
python -m pytest backend\tests
```

To build the frontend for production:

```powershell
Set-Location frontend
npm run build
```
