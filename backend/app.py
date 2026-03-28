import json
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict

import firebase_admin
import jwt
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))


def _init_firestore_client():
    if firebase_admin._apps:
        return firestore.client()

    service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if service_account_path:
        if not os.path.isabs(service_account_path):
            service_account_path = os.path.join(BASE_DIR, service_account_path)
        cred = credentials.Certificate(service_account_path)
    elif service_account_json:
        cred = credentials.Certificate(json.loads(service_account_json))
    else:
        raise RuntimeError(
            "Firebase service account is not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH "
            "or FIREBASE_SERVICE_ACCOUNT_JSON."
        )

    firebase_admin.initialize_app(cred)
    return firestore.client()


db = _init_firestore_client()


def _create_token(user_id: str, mobile: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "mobile": mobile,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header."}), 401

        token = auth_header.replace("Bearer ", "", 1).strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token."}), 401

        return fn(*args, **kwargs)

    return wrapper


def _serialize_user(user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user_id,
        "name": user_data.get("name"),
        "mobile": user_data.get("mobile"),
        "onboarding": user_data.get("onboarding", {}),
        "onboardingCompleted": bool(user_data.get("onboardingCompleted", False)),
    }


@app.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "backend"}), 200


@app.get("/")
def index():
    return jsonify({"message": "Flask backend is running"}), 200


@app.post("/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    mobile = str(payload.get("mobile", "")).strip()
    password = str(payload.get("password", ""))

    if not name or not mobile or not password:
        return jsonify({"error": "name, mobile and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    existing_query = db.collection("users").where("mobile", "==", mobile).limit(1).stream()
    existing_user = next(existing_query, None)
    if existing_user is not None:
        return jsonify({"error": "User already exists with this mobile number."}), 409

    now = firestore.SERVER_TIMESTAMP
    user_doc = {
        "name": name,
        "mobile": mobile,
        "passwordHash": generate_password_hash(password),
        "onboarding": {},
        "onboardingCompleted": False,
        "createdAt": now,
        "updatedAt": now,
    }

    user_ref = db.collection("users").document()
    user_ref.set(user_doc)

    token = _create_token(user_ref.id, mobile)

    return (
        jsonify(
            {
                "token": token,
                "user": _serialize_user(user_ref.id, user_doc),
            }
        ),
        201,
    )


@app.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    mobile = str(payload.get("mobile", "")).strip()
    password = str(payload.get("password", ""))

    if not mobile or not password:
        return jsonify({"error": "mobile and password are required."}), 400

    user_query = db.collection("users").where("mobile", "==", mobile).limit(1).stream()
    user_doc = next(user_query, None)
    if user_doc is None:
        return jsonify({"error": "Invalid mobile or password."}), 401

    user_data = user_doc.to_dict() or {}
    if not check_password_hash(str(user_data.get("passwordHash", "")), password):
        return jsonify({"error": "Invalid mobile or password."}), 401

    token = _create_token(user_doc.id, mobile)

    return jsonify({"token": token, "user": _serialize_user(user_doc.id, user_data)}), 200


@app.post("/onboarding")
@_require_auth
def save_onboarding():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or len(payload) == 0:
        return jsonify({"error": "Onboarding payload is required."}), 400

    user_id = request.user.get("sub")
    if not user_id:
        return jsonify({"error": "Invalid token payload."}), 401

    user_ref = db.collection("users").document(user_id)
    if not user_ref.get().exists:
        return jsonify({"error": "User not found."}), 404

    user_ref.set(
        {
            "onboarding": payload,
            "onboardingCompleted": True,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "onboardingUpdatedAt": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    return jsonify({"message": "Onboarding saved successfully."}), 200


@app.get("/auth/me")
@_require_auth
def me():
    user_id = request.user.get("sub")
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify({"error": "User not found."}), 404

    return jsonify({"user": _serialize_user(user_doc.id, user_doc.to_dict() or {})}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
