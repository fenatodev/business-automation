"""Run explicitly: python -m app.worker [--once]. Never starts from the API."""
import argparse
import time

from app.database import SessionLocal, settings
from app.services.internal_tasks import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        worked = run_once(SessionLocal, settings.intake_service_context)
        if args.once:
            return
        if not worked:
            time.sleep(1)


if __name__ == "__main__":
    main()
