## Real email delivery

This backend can send emails using **Gmail API (recommended)**, with **SMTP** as a fallback.

### Option A: Gmail API (recommended)

1) Create a Google Cloud OAuth client (Desktop app) and download the client secrets JSON.

2) Set env vars:

- `EMAIL_PROVIDER=gmail`
- `GMAIL_CLIENT_SECRETS=/absolute/path/to/client_secret.json`
- `GMAIL_TOKEN_FILE=/Users/karanvazirani/Desktop/sentinel-ai/backend/gmail_token.json` (optional; default is `backend/gmail_token.json`)

3) Start the backend and send a draft.

The first time you send, an OAuth browser flow will open and the token will be stored in `GMAIL_TOKEN_FILE`.

### Option B: SMTP (fallback or explicit)

Set env vars:

- `EMAIL_PROVIDER=smtp`
- `SMTP_HOST=...`
- `SMTP_PORT=587`
- `SMTP_USER=...`
- `SMTP_PASSWORD=...`
- `SMTP_FROM=...` (optional; defaults to `SMTP_USER`)
- `SMTP_TLS=true`

### Install deps

If you’re using a virtualenv:

```bash
pip install -r /Users/karanvazirani/Desktop/sentinel-ai/backend/requirements.txt
```

