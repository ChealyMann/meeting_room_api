"""Runs the expiry job every `expiry_interval_seconds` in a daemon thread (spec 10.2, B-03).

Only one process may run the job. The runner keeps its own database connection open and
holds the MySQL lock `booking_expiry` on it (`GET_LOCK(name, 0)` does not wait). A lock
belongs to its connection, so if the process dies, MySQL frees the lock and another
process takes it at its next tick.
"""

import logging
import threading

from sqlalchemy import Connection, text

from app import db
from app.config import Settings
from app.services import booking_expiry

logger = logging.getLogger(__name__)

LOCK_NAME = "booking_expiry"


class ExpiryRunner:
    def __init__(self, settings: Settings) -> None:
        self._interval = settings.expiry_interval_seconds
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._connection: Connection | None = None
        self._has_lock = False

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="expiry-job", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join()
        self._close()

    def tick(self) -> bool:
        """One step: take the lock if needed, then run the job. False without the lock."""
        if not self._hold_lock():
            return False
        with db.SessionLocal() as session:
            booking_expiry.run_once(session)
        return True

    def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("Expiry job failed. It runs again at the next tick.")
                self._drop_connection()
            self._stopping.wait(self._interval)

    def _hold_lock(self) -> bool:
        if self._connection is None:
            self._connection = db.engine.connect()
        params = {"name": LOCK_NAME}
        if self._has_lock:
            # Still ours? (A lost connection loses the lock.)
            sql = "SELECT IS_USED_LOCK(:name) = CONNECTION_ID()"
            self._has_lock = self._connection.scalar(text(sql), params) == 1
        if not self._has_lock:
            sql = "SELECT GET_LOCK(:name, 0)"
            self._has_lock = self._connection.scalar(text(sql), params) == 1
        self._connection.rollback()  # end the transaction SQLAlchemy began; locks stay
        return self._has_lock

    def _close(self) -> None:
        """Release the lock and close the connection (on shutdown)."""
        if self._connection is None:
            return
        try:
            if self._has_lock:
                self._connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME})
            self._connection.close()
        except Exception:
            logger.exception("Could not release the expiry lock.")
            self._drop_connection()
        self._connection = None
        self._has_lock = False

    def _drop_connection(self) -> None:
        """After an error: throw the connection away. Closing it in MySQL frees the lock."""
        if self._connection is not None:
            try:
                self._connection.invalidate()
                self._connection.close()
            except Exception:
                logger.exception("Could not close the expiry connection.")
        self._connection = None
        self._has_lock = False
