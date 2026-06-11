import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.fernet import Fernet, InvalidToken

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# settings
BASE_URL = "http://localhost:8005"
EMAIL = "demo@cra.local"
PASSWORD = "demo1234"
SESSION_FILE = Path(".portalite_session.bin")
# fixed key so the session file can be decrypted on the next run
ENCRYPTION_KEY = b"wdm-Xaga6eGTpoznjYNOwZ43sE_bBqPhRbIw1pFVg6k="


def login() -> dict:
    # send email and password to the server and get a token back
    resp = httpx.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code == 401:
        raise RuntimeError("Wrong email or password")
    resp.raise_for_status()

    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Server did not return a token")

    logger.info("Login successful")
    session = {
        "token": token,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return session


def save_session(session: dict) -> None:
    # encrypt the session and write it to a file
    fernet = Fernet(ENCRYPTION_KEY)
    raw = json.dumps(session).encode()
    SESSION_FILE.write_bytes(fernet.encrypt(raw))
    logger.info("Session saved to %s", SESSION_FILE)


def load_session() -> dict | None:
    # read and decrypt the session file if it exists
    if not SESSION_FILE.exists():
        return None
    try:
        fernet = Fernet(ENCRYPTION_KEY)
        raw = fernet.decrypt(SESSION_FILE.read_bytes())
        logger.info("Reusing saved session from %s", SESSION_FILE)
        return json.loads(raw)
    except InvalidToken:
        logger.warning("Could not decrypt session file — will log in again")
        return None


def get_session() -> dict:
    # load from disk if possible otherwise log in
    session = load_session()
    if session is None:
        session = login()
        save_session(session)
    return session


def make_request(session: dict, method: str, path: str, **kwargs) -> httpx.Response:
    # send a request with the token in the header
    headers = {"Authorization": f"Bearer {session['token']}"}
    resp = httpx.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)

    # if the token was rejected log in again and retry
    if resp.status_code in (401, 403):
        logger.info("Token rejected, logging in again…")
        session = login()
        save_session(session)
        headers = {"Authorization": f"Bearer {session['token']}"}
        resp = httpx.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)

    resp.raise_for_status()
    return resp


def main() -> None:
    print("=" * 60)
    print("  Portalite session demo")
    print("=" * 60)

    # test 1 — logs in if no saved session exists
    print("\n 1 - First request — logs in if no saved session")
    session = get_session()
    me = make_request(session, "GET", "/api/auth/me").json()
    print(f"    Authenticated as: {me['email']}  (role: {me['role']})")

    # test 2 — reuses the same session in memory
    print("\n 2 - Second request — reuses session in memory (no new login)")
    me2 = make_request(session, "GET", "/api/auth/me").json()
    print(f"    Still authenticated as: {me2['email']}")

    # test 3 — loads the session from disk
    print("\n 3 - Third request — loads session from disk (no new login)")
    session2 = get_session()
    me3 = make_request(session2, "GET", "/api/auth/me").json()
    print(f"    Disk-loaded session works: {me3['email']}")

    print("\n All three requests succeeded.\n")


if __name__ == "__main__":
    main()