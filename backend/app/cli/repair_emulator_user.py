from argparse import ArgumentParser
from getpass import getpass

from firebase_admin import auth
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.db.session import SessionLocal
from app.models import User
from app.services.audit import record_audit_event


def prompt_password() -> str:
    while True:
        password = getpass("Yeni parola: ")
        confirmation = getpass("Yeni parolayı tekrar girin: ")
        if len(password) < 8:
            print("Parola en az 8 karakter olmalıdır.")
            continue
        if password != confirmation:
            print("Parolalar eşleşmiyor.")
            continue
        return password


def repair_identity(user: User, *, reset_password: bool = False) -> str:
    if not get_settings().firebase_use_emulator:
        raise SystemExit(
            "Bu komut yalnızca Firebase Auth Emulator kullanılırken çalıştırılabilir."
        )

    firebase_app = get_firebase_app()
    try:
        firebase_user = auth.get_user(user.firebase_uid, app=firebase_app)
    except auth.UserNotFoundError:
        try:
            email_owner = auth.get_user_by_email(user.email, app=firebase_app)
        except auth.UserNotFoundError:
            email_owner = None
        if email_owner is not None:
            raise SystemExit(
                "Emülatörde aynı e-posta farklı bir Firebase UID ile kayıtlı. "
                "Çakışan hesabı incelemeden otomatik değişiklik yapılmadı."
            ) from None

        auth.create_user(
            uid=user.firebase_uid,
            email=user.email,
            password=prompt_password(),
            display_name=user.full_name,
            email_verified=False,
            disabled=not user.is_active,
            app=firebase_app,
        )
        return "restored"

    if firebase_user.email != user.email:
        raise SystemExit(
            "Firebase UID mevcut ancak e-posta PostgreSQL kaydıyla eşleşmiyor. "
            "Otomatik değişiklik yapılmadı."
        )
    if not reset_password:
        return "matched"

    auth.update_user(
        user.firebase_uid,
        password=prompt_password(),
        disabled=not user.is_active,
        app=firebase_app,
    )
    return "password_reset"


def main() -> None:
    parser = ArgumentParser(
        description="PostgreSQL kullanıcısını Firebase Auth Emulator ile yeniden eşleştirir."
    )
    parser.add_argument("--email", help="Onarılacak kullanıcının e-posta adresi.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Hesap zaten varsa parolasını yeniler.",
    )
    args = parser.parse_args()
    email = (args.email or input("E-posta: ")).strip().lower()
    if not email:
        raise SystemExit("E-posta boş bırakılamaz.")

    with SessionLocal() as session:
        user = session.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            raise SystemExit("Bu e-posta PostgreSQL veritabanında bulunamadı.")

        result = repair_identity(user, reset_password=args.reset_password)
        if result == "matched":
            print(f"PostgreSQL ve Firebase hesabı zaten eşleşiyor: {user.email}")
            return

        record_audit_event(
            session,
            action=(
                "user.firebase_identity_restored"
                if result == "restored"
                else "user.firebase_password_reset"
            ),
            entity_type="user",
            entity_id=user.id,
            after={"firebase_uid": user.firebase_uid, "is_active": user.is_active},
            context={"source": "cli", "provider": "firebase_emulator"},
        )
        session.commit()
        operation = "yeniden oluşturuldu" if result == "restored" else "parolası yenilendi"
        print(f"Firebase Emulator hesabı {operation}: {user.email}")


if __name__ == "__main__":
    main()
