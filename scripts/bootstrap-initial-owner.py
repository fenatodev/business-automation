#!/usr/bin/env python3
"""Create the one initial active owner for an existing company.

Run manually in a controlled environment. The password is prompted rather than
accepted on the command line, and the command refuses to run once any user
exists.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.auth import bootstrap_initial_owner, normalize_email


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--company-id", required=True, type=int)
    args = parser.parse_args()

    email = normalize_email(args.email)
    if not email or len(email) > 320:
        parser.error("--email must contain between 1 and 320 characters")

    password = getpass.getpass("Initial owner password: ")
    if not 1 <= len(password) <= 1024:
        parser.error("password must contain between 1 and 1024 characters")

    db = SessionLocal()
    try:
        user = bootstrap_initial_owner(
            db,
            email=email,
            password=password,
            company_id=args.company_id,
        )
        db.commit()
        user_id = user.id
    except ValueError as error:
        db.rollback()
        print(f"Bootstrap failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        db.close()

    print(f"Initial owner created with user id {user_id}.")


if __name__ == "__main__":
    main()
