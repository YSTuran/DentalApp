from getpass import getpass

from firebase_admin import auth
from sqlalchemy import func, select

from app.core.firebase import get_firebase_app
from app.db.session import SessionLocal
from app.models import RoleCode, User, UserRoleAssignment


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(label).strip()
        if value:
            return value
        print("Bu alan boş bırakılamaz.")


def prompt_password() -> str:
    while True:
        password = getpass("Parola: ")
        confirmation = getpass("Parolayı tekrar girin: ")

        if len(password) < 12:
            print("Parola en az 12 karakter olmalıdır.")
            continue
        if password != confirmation:
            print("Parolalar eşleşmiyor.")
            continue
        return password


def main() -> None:
    print("DentalApp ilk sistem yöneticisi")
    full_name = prompt_non_empty("Ad soyad: ")
    email = prompt_non_empty("E-posta: ").lower()
    password = prompt_password()

    with SessionLocal() as session:
        existing = session.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None:
            raise SystemExit("Bu e-posta PostgreSQL'de zaten kayıtlı.")

    firebase_user = auth.create_user(
        email=email,
        password=password,
        display_name=full_name,
        email_verified=False,
        app=get_firebase_app(),
    )

    try:
        with SessionLocal.begin() as session:
            user = User(
                firebase_uid=firebase_user.uid,
                email=email,
                full_name=full_name,
            )
            session.add(user)
            session.flush()
            session.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role=RoleCode.SYSTEM_ADMIN,
                    clinic_id=None,
                )
            )
    except Exception:
        auth.delete_user(firebase_user.uid, app=get_firebase_app())
        raise

    print(f"Sistem yöneticisi oluşturuldu: {email}")


if __name__ == "__main__":
    main()
