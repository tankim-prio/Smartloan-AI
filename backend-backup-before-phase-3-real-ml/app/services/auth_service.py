from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 260000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )

    encoded_hash = base64.b64encode(password_hash).decode("utf-8")

    return f"pbkdf2_sha256${iterations}${salt}${encoded_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_text, salt, stored_hash = hashed_password.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )

        encoded_hash = base64.b64encode(password_hash).decode("utf-8")

        return hmac.compare_digest(encoded_hash, stored_hash)

    except Exception:
        return False


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_user(
    db: Session,
    full_name: str,
    email: str,
    phone: str | None,
    password: str,
    role: str = "user",
) -> User:
    existing_user = get_user_by_email(db, email)

    if existing_user:
        raise ValueError("User already exists")

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    expire_minutes = settings.access_token_expire_minutes

    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=expire_minutes)
    )

    payload = data.copy()
    payload["exp"] = int(expire.timestamp())

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }

    header_encoded = _base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )

    payload_encoded = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    signing_input = f"{header_encoded}.{payload_encoded}".encode("utf-8")

    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    signature_encoded = _base64url_encode(signature)

    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        header_encoded, payload_encoded, signature_encoded = token.split(".")

        signing_input = f"{header_encoded}.{payload_encoded}".encode("utf-8")

        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

        actual_signature = _base64url_decode(signature_encoded)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        payload = json.loads(_base64url_decode(payload_encoded).decode("utf-8"))

        exp = payload.get("exp")

        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None

        return payload

    except Exception:
        return None
