import secrets
import string

from firebase_admin import auth, exceptions

from app.core.firebase import get_firebase_app


class FirebaseIdentityError(Exception):
    pass


class FirebaseIdentityConflictError(FirebaseIdentityError):
    pass


class FirebaseIdentityNotFoundError(FirebaseIdentityError):
    pass


def generate_temporary_password(length: int = 20) -> str:
    if length < 16:
        raise ValueError("Geçici parola en az 16 karakter olmalıdır.")

    alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%*-_"),
    ]
    remaining = [secrets.choice(alphabet) for _ in range(length - len(required))]
    characters = required + remaining
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def create_identity(*, email: str, full_name: str, password: str) -> str:
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=full_name,
            email_verified=False,
            disabled=False,
            app=get_firebase_app(),
        )
        return user.uid
    except (auth.EmailAlreadyExistsError, auth.UidAlreadyExistsError) as error:
        raise FirebaseIdentityConflictError from error
    except exceptions.FirebaseError as error:
        raise FirebaseIdentityError from error


def update_identity_name(firebase_uid: str, full_name: str) -> None:
    try:
        auth.update_user(firebase_uid, display_name=full_name, app=get_firebase_app())
    except auth.UserNotFoundError as error:
        raise FirebaseIdentityNotFoundError from error
    except exceptions.FirebaseError as error:
        raise FirebaseIdentityError from error


def set_identity_disabled(firebase_uid: str, *, disabled: bool) -> None:
    try:
        auth.update_user(firebase_uid, disabled=disabled, app=get_firebase_app())
    except auth.UserNotFoundError as error:
        raise FirebaseIdentityNotFoundError from error
    except exceptions.FirebaseError as error:
        raise FirebaseIdentityError from error


def delete_identity(firebase_uid: str) -> None:
    try:
        auth.delete_user(firebase_uid, app=get_firebase_app())
    except auth.UserNotFoundError:
        return
    except exceptions.FirebaseError as error:
        raise FirebaseIdentityError from error
