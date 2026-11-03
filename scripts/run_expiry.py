"""Run the expiry job once (spec 10.3): reject waiting bookings whose first session has
started and confirm bookings still in IT setup.

Usage (from the project folder):  python -m scripts.run_expiry
"""

import sys

from app.db import SessionLocal
from app.services.booking_expiry import run_once


def main() -> int:
    with SessionLocal() as session:
        result = run_once(session)
    print(f"Rejected: {len(result.rejected)}, confirmed: {len(result.confirmed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
