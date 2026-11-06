import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.errors import register_error_handlers
from app.expiry_runner import ExpiryRunner
from app.middleware import RequestIdLogFilter, RequestIdMiddleware
from app.routers import (
    admin_bookings,
    auth,
    bookings,
    buildings,
    categories,
    catering_orders,
    catering_packages,
    departments,
    divisions,
    equipment,
    floors,
    health,
    it_services,
    it_staff,
    it_tickets,
    locations,
    me,
    owner_bookings,
    pitika_bookings,
    positions,
    provinces,
    public_holidays,
    roles,
    room_equipment,
    room_photos,
    room_schedule,
    rooms,
    users,
)
from app.services.login_rate_limit import LoginRateLimiter

API_PREFIX = "/api/v1"


def configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
        )
    for handler in root.handlers:
        if not any(isinstance(f, RequestIdLogFilter) for f in handler.filters):
            handler.addFilter(RequestIdLogFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Starts the expiry job (B-03) when it is on, and stops it at shutdown."""
    settings: Settings = app.state.settings
    runner = ExpiryRunner(settings) if settings.expiry_job_enabled else None
    app.state.expiry_runner = runner
    if runner is not None:
        runner.start()
    try:
        yield
    finally:
        if runner is not None:
            await asyncio.to_thread(runner.stop)  # stop() waits for the thread
        app.state.expiry_runner = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    app = FastAPI(title="Room Booking API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.login_limiter = LoginRateLimiter()
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(me.router)
    api.include_router(provinces.router)
    api.include_router(locations.router)
    api.include_router(buildings.router)
    api.include_router(floors.router)
    api.include_router(categories.router)
    api.include_router(equipment.router)
    api.include_router(departments.router)
    api.include_router(divisions.router)
    api.include_router(positions.router)
    api.include_router(roles.router)
    api.include_router(users.router)
    api.include_router(rooms.router)
    api.include_router(room_photos.router)
    api.include_router(room_schedule.router)
    api.include_router(room_equipment.router)
    api.include_router(catering_packages.router)
    api.include_router(it_services.router)
    api.include_router(it_tickets.router)
    api.include_router(it_staff.router)
    api.include_router(pitika_bookings.router)
    api.include_router(owner_bookings.router)
    api.include_router(catering_orders.router)
    api.include_router(public_holidays.router)
    api.include_router(bookings.router)
    api.include_router(admin_bookings.router)
    app.include_router(api)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    # Added last so it is the outermost middleware and sees every response.
    app.add_middleware(RequestIdMiddleware)
    return app


app = create_app()
