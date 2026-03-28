# Flask Backend

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
export JWT_SECRET="your-strong-secret"
export FIREBASE_SERVICE_ACCOUNT_PATH="/absolute/path/to/firebase-service-account.json"
flask --app app run --debug --host=0.0.0.0 --port=5000
```

You can also provide Firebase credentials via `FIREBASE_SERVICE_ACCOUNT_JSON` (stringified JSON).

Optional variables:

- `JWT_EXPIRY_HOURS` (default: `24`)

## Endpoints

- `GET /` -> basic service message
- `GET /health` -> health check
- `POST /auth/signup` -> signup with `name`, `mobile`, `password`, returns JWT + user
- `POST /auth/login` -> login with `mobile`, `password`, returns JWT + user
- `GET /auth/me` -> fetch signed-in user (requires `Authorization: Bearer <token>`)
- `POST /onboarding` -> save onboarding payload to signed-in user in Firebase (requires JWT)
