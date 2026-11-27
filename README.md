# AI-Powered Data Analysis Tool

A web application for uploading tabular datasets and exploring analysis, preprocessing, and AI-assisted visualization workflows. The backend is built with FastAPI; the frontend is a React application bundled with Vite.

## Features

- Upload CSV, XLS, XLSX, JSON, and TSV datasets (up to 100 MB).
- Browse uploaded datasets in the web interface.
- Use the FastAPI endpoints for summaries, preprocessing profiles and transformations, and chart suggestions/rendering.
- Enable Gemini-backed summaries and suggestions by configuring `GEMINI_API_KEY`.
- Persist dataset metadata in SQLite and uploaded/processed files on disk.

## Run locally with Docker Compose

Requirements: Docker Engine and Docker Compose.

```bash
cp .env.example .env
# Optionally edit .env and set GEMINI_API_KEY.
docker compose up --build
```

Open the frontend at <http://localhost:5173> and the API documentation at <http://localhost:8000/docs>. The frontend proxies API requests to the backend within the Compose network. AI features remain disabled when `GEMINI_API_KEY` is unset.

## Run without Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY=your_key  # Optional; Windows PowerShell: $env:GEMINI_API_KEY="your_key"
uvicorn app.main:app --reload --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
node --version  # Node.js 22 or newer
npm ci
npm run dev
```

The Vite development server proxies `/api` requests to `http://localhost:8000`. Set `VITE_API_BASE` if the API runs at another URL.

## API endpoints

Interactive API documentation is available at `/docs` when the backend is running. Main routes include:

- `POST /api/upload/dataset` and `GET /api/upload/datasets`
- `POST /api/analysis/{dataset_id}/summary`
- `POST /api/preprocessing/{dataset_id}/profile` and `/apply`
- `GET /api/visualization/{dataset_id}/suggest` and `POST /render`

## Storage and deployment notes

The default storage is local SQLite plus local files under `backend/app/storage`. Keep that directory on a persistent volume to retain uploaded datasets and metadata across container restarts. This setup is intended for local demos and single-instance use; it does not include user authentication or authorization, and should not be exposed publicly or used with sensitive datasets as-is. Use an appropriately secured database, object storage, access controls, and operational monitoring before production deployment.

Do not commit `.env` files, uploaded datasets, generated files, or credentials. The example environment file contains no secrets.

## Development checks

```bash
cd backend && PYTHONPATH=. pytest -q
cd frontend && npm ci && npm run build
```

GitHub Actions runs the backend tests and frontend production build on pushes and pull requests.
