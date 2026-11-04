from app.constants.booking import ReviewStage
from app.schemas.common import OptionalBookingText, RequestModel, ResponseModel


class AdminActionsOut(ResponseModel):
    """What the Admin may do with a booking now (B-33, B-34). `stage`: the review step that
    approve and reject would decide, or null."""

    cancel: bool
    approve: bool
    reject: bool
    stage: ReviewStage | None


class AdminRejectBody(RequestModel):
    """The reason is optional for the Admin (D-35); `version` is the booking version seen."""

    reason: OptionalBookingText(1000, min_length=5) = None
    version: int
