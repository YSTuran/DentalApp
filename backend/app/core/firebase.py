import os
import socket
from functools import lru_cache
from pathlib import Path

import firebase_admin
from firebase_admin import App, credentials

from app.core.config import get_settings

FIREBASE_APP_NAME = "dentalapp"


@lru_cache
def get_firebase_app() -> App:
    settings = get_settings()

    try:
        return firebase_admin.get_app(FIREBASE_APP_NAME)
    except ValueError:
        pass

    options = {"projectId": settings.firebase_project_id}

    if settings.firebase_use_emulator:
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = settings.firebase_auth_emulator_host
        return firebase_admin.initialize_app(options=options, name=FIREBASE_APP_NAME)

    credential_path = settings.firebase_credentials_path
    if credential_path is None or not Path(credential_path).is_file():
        raise RuntimeError("Firebase service account file is not configured or does not exist.")

    credential = credentials.Certificate(str(credential_path))
    return firebase_admin.initialize_app(
        credential=credential,
        options=options,
        name=FIREBASE_APP_NAME,
    )


def check_firebase() -> bool:
    settings = get_settings()

    try:
        get_firebase_app()
        if not settings.firebase_use_emulator:
            return True

        host, separator, port = settings.firebase_auth_emulator_host.rpartition(":")
        if not separator or not host or not port.isdigit():
            return False

        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except (OSError, RuntimeError, ValueError):
        return False
