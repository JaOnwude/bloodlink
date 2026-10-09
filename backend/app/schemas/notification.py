"""Response models for the text-message alerts sent about a request."""

from pydantic import BaseModel


class AlertSummary(BaseModel):
    """How many donors have been alerted about a request, by delivery state.

    Attributes:
        provider: The sender currently in use: ``termii`` for real messages, ``console``
            when messages are only recorded, for example while no sender ID is approved.
    """

    sent: int
    failed: int
    queued: int
    total: int
    provider: str


class AlertRunRead(BaseModel):
    """What one request to alert donors did, followed by the request's totals."""

    matched: int
    newly_alerted: int
    sent: int
    failed: int
    already_alerted: int
    without_phone: int
    totals: AlertSummary
