from datetime import timedelta
from time import time
from typing import Any

from firebase_admin import auth, exceptions

from app.core.config import get_settings
from app.core.firebase import get_firebase_app


class FirebaseAuthenticationError(Exception):
    """Raised when a Firebase token or session cannot be trusted."""


class RecentSignInRequiredError(FirebaseAuthenticationError):
    """Raised when an ID token was not issued by a recent sign-in."""


class FirebaseServiceError(Exception):
    """Raised when Firebase cannot complete an authentication operation."""


def verify_id_token(id_token: str) -> dict[str, Any]:
    try:
        return auth.verify_id_token(
            id_token,
            app=get_firebase_app(),
            check_revoked=True,
        )
    except (
        auth.InvalidIdTokenError,
        auth.ExpiredIdTokenError,
        auth.RevokedIdTokenError,
        auth.UserDisabledError,
    ) as exc:
        raise FirebaseAuthenticationError from exc
    except exceptions.FirebaseError as exc:
        raise FirebaseServiceError from exc


def create_session_cookie(id_token: str) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    claims = verify_id_token(id_token)
    auth_time = claims.get("auth_time")

    if not isinstance(auth_time, int | float) or time() - auth_time > 5 * 60:
        raise RecentSignInRequiredError

    expires_in = timedelta(days=settings.firebase_session_days)
    try:
        session_cookie = auth.create_session_cookie(
            id_token,
            expires_in=expires_in,
            app=get_firebase_app(),
        )
    except auth.InvalidIdTokenError as exc:
        raise FirebaseAuthenticationError from exc
    except exceptions.FirebaseError as exc:
        raise FirebaseServiceError from exc

    if isinstance(session_cookie, bytes):
        session_cookie = session_cookie.decode("utf-8")

    return session_cookie, claims


def verify_session_cookie(session_cookie: str) -> dict[str, Any]:
    try:
        return auth.verify_session_cookie(
            session_cookie,
            app=get_firebase_app(),
            check_revoked=True,
        )
    except (
        auth.InvalidSessionCookieError,
        auth.ExpiredSessionCookieError,
        auth.RevokedSessionCookieError,
        auth.UserDisabledError,
    ) as exc:
        raise FirebaseAuthenticationError from exc
    except exceptions.FirebaseError as exc:
        raise FirebaseServiceError from exc
