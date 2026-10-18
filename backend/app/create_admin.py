"""Explicit interactive first-administrator provisioning; never auto-seeded in production."""
import getpass
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import User
from .security import hash_password

def main():
    Base.metadata.create_all(engine)
    email = input('Administrator email: ').strip().lower()
    name = input('Administrator name: ').strip()
    password = getpass.getpass('New password (at least 12 characters): ')
    confirmation = getpass.getpass('Confirm password: ')
    if '@' not in email or len(name) < 2 or len(password) < 12 or password != confirmation:
        raise SystemExit('Invalid email, name or password confirmation. No account created.')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit('This email already exists. No account changed.')
        db.add(User(name=name, email=email, password_hash=hash_password(password), role='admin', active=True))
        db.commit()
    print('Administrator created.')

if __name__ == '__main__':
    main()
