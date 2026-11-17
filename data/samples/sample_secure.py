# SAMPLE FILE: Clean, well-written code — should produce APPROVE verdict
# This is SYNTHETIC code — not from any real system

import os
import hashlib
import hmac


def get_database_password() -> str:
    """Read DB password from environment — never hardcode."""
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise EnvironmentError("DB_PASSWORD environment variable not set")
    return password


def hash_password(password: str) -> str:
    """Hash password with bcrypt-strength algorithm."""
    salt = os.urandom(16)
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def verify_token(token: str, secret: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    expected = hmac.new(secret.encode(), digestmod="sha256").hexdigest()
    return hmac.compare_digest(token, expected)


def fetch_order(cursor, order_id: str) -> dict:
    """Use parameterised queries — not string concatenation."""
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if row is None:
        return {}
    return {"id": row[0], "status": row[1], "amount": row[2]}
