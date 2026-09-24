from getpass import getpass

from firebase_admin import auth
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.db.session import SessionLocal
from app.models import RoleCode, User, UserRoleAssignment
from app.services.audit import record_audit_event


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

        if len(password) < 8:
            print("Parola en az 8 karakter olmalıdır.")
            continue
        if password != confirmation:
            print("Parolalar eşleşmiyor.")
            continue
        return password


def restore_emulator_admin(user: User) -> None:
    settings = get_settings()
    if not settings.firebase_use_emulator:
        raise SystemExit(
            "PostgreSQL kaydı zaten var. Gerçek Firebase kullanıcısı otomatik olarak "
            "yeniden oluşturulmadı."
        )

    firebase_app = get_firebase_app()
    try:
        firebase_user = auth.get_user(user.firebase_uid, app=firebase_app)
    except auth.UserNotFoundError:
        try:
            firebase_user_with_email = auth.get_user_by_email(user.email, app=firebase_app)
        except auth.UserNotFoundError:
            firebase_user_with_email = None

        if firebase_user_with_email is not None:
            raise SystemExit(
                "Emülatörde aynı e-posta farklı bir Firebase UID ile kayıtlı. "
                "Bu kullanıcıyı Emulator UI üzerinden kaldırıp komutu yeniden çalıştırın."
            ) from None

        print(
            "PostgreSQL kaydı bulundu ancak Firebase Auth Emulator kullanıcısı eksik. "
            "Kullanıcı aynı UID ile yeniden oluşturulacak."
        )
        password = prompt_password()
        auth.create_user(
            uid=user.firebase_uid,
            email=user.email,
            password=password,
            display_name=user.full_name,
            email_verified=False,
            app=firebase_app,
        )
        print(f"Emülatör kullanıcısı geri yüklendi: {user.email}")
        return

    if firebase_user.email != user.email:
        raise SystemExit(
            "Firebase UID mevcut ancak e-posta PostgreSQL kaydıyla eşleşmiyor. "
            "Otomatik değişiklik yapılmadı."
        )

    print(f"Sistem yöneticisi zaten eşleşmiş durumda: {user.email}")


def main() -> None:
    print("DentalApp ilk sistem yöneticisi")
    email = prompt_non_empty("E-posta: ").lower()

    with SessionLocal() as session:
        existing = session.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None:
            is_system_admin = session.scalar(
                select(UserRoleAssignment.id).where(
                    UserRoleAssignment.user_id == existing.id,
                    UserRoleAssignment.role == RoleCode.SYSTEM_ADMIN,
                    UserRoleAssignment.clinic_id.is_(None),
                    UserRoleAssignment.is_active.is_(True),
                )
            )
            if not existing.is_active or is_system_admin is None:
                raise SystemExit(
                    "Bu e-posta PostgreSQL'de kayıtlı ancak aktif bir sistem yöneticisi değil."
                )

    if existing is not None:
        restore_emulator_admin(existing)
        return

    full_name = prompt_non_empty("Ad soyad: ")
    password = prompt_password()

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
            record_audit_event(
                session,
                action="system.bootstrap_admin_created",
                entity_type="user",
                entity_id=user.id,
                after={
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": [RoleCode.SYSTEM_ADMIN],
                },
                context={"source": "cli"},
            )
    except Exception:
        auth.delete_user(firebase_user.uid, app=get_firebase_app())
        raise

    print(f"Sistem yöneticisi oluşturuldu: {email}")


if __name__ == "__main__":
    main()
