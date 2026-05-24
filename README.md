# Breathe ESG Ingestion Prototype

Focused Django REST + React prototype for ingesting messy enterprise activity data, normalizing it, and supporting analyst review before audit lock.

## What It Does

- Ingests three realistic CSV source shapes:
  - SAP fuel/procurement export
  - Utility electricity portal export
  - Corporate travel export inspired by Concur/Navan
- Normalizes rows into auditable activity records.
- Flags suspicious or failed records.
- Lets analysts approve, reject, edit, and lock records.
- Tracks source system, import batch, raw payload, normalized units, review state, and audit events.

## Demo Credentials

Seed data creates:

- Username: `analyst@acme.example`
- Password: `demo12345`
- Tenant: `Acme Manufacturing`

## Local Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

API runs at `http://127.0.0.1:8000/api/`.

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://127.0.0.1:5173`.

## Deployment Notes

For Render/Railway:

- Backend start command: `gunicorn config.wsgi:application`
- Backend build command: `pip install -r backend/requirements.txt && python backend/manage.py migrate`
- Set `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS`.
- Frontend build command: `npm install && npm run build`
- Set `VITE_API_BASE_URL` to the deployed backend URL.

## Required Assignment Docs

- [MODEL.md](MODEL.md)
- [DECISIONS.md](DECISIONS.md)
- [TRADEOFFS.md](TRADEOFFS.md)
- [SOURCES.md](SOURCES.md)
