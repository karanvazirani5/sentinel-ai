## Deploying Sentinel to Render

This is a minimal path to get a **real, hosted** version of Sentinel running so a business can try it.

### 1. Prerequisites

- A Render account
- This repo pushed to GitHub

### 2. Backend (FastAPI) service

1. In Render, click **New → Web Service**.
2. Choose your GitHub repo.
3. In the configuration:
   - **Root Directory**: `backend`
   - **Environment**: `Docker`
   - Render will auto-detect `backend/Dockerfile`.
4. Set environment variables (for email sending, optional at first):

   For Gmail API:

   - `EMAIL_PROVIDER=gmail`
   - `GMAIL_CLIENT_SECRETS=/app/client_secret.json`

   Then upload `client_secret.json` as a Render secret file and mount it at `/app/client_secret.json`.

   Or for SMTP:

   - `EMAIL_PROVIDER=smtp`
   - `SMTP_HOST=...`
   - `SMTP_PORT=587`
   - `SMTP_USER=...`
   - `SMTP_PASSWORD=...`
   - `SMTP_FROM=...` (optional)

5. Deploy. You’ll get a backend URL like:

   `https://sentinel-backend.onrender.com`

### 3. Frontend (Next.js) service

You have two options; the simplest is another Docker-based web service.

1. In Render, click **New → Web Service** again.
2. Select the same repo.
3. Config:
   - **Root Directory**: `web`
   - **Environment**: `Docker`
   - Render will use `web/Dockerfile`.
4. Environment variables:

   - `NEXT_PUBLIC_API_URL=https://sentinel-backend.onrender.com`
   - `NODE_ENV=production`

5. Deploy. You’ll get a frontend URL like:

   `https://sentinel-web.onrender.com`

Open that URL in a browser; the app will talk to your hosted backend.

### 4. Local Docker compose (optional, for testing)

You can test the same setup locally:

```bash
cd /path/to/sentinel-ai
docker compose up --build
```

Then:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### 5. Next steps for production readiness

- Swap SQLite for Render Postgres by changing `DATABASE_URL` in `backend/main.py`.
- Add simple auth (login) if you want to host multiple businesses in one deployment.

