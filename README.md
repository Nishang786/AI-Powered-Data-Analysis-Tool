# Docker Compose

From the project root run:

```powershell
docker-compose build
docker-compose up
```

The backend will be available at http://localhost:8000 and the frontend at http://localhost:5173

Make sure to set `GEMINI_API_KEY` in `backend/.env` if you want LLM features enabled.

