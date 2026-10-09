"""Sending text messages, through Termii or to the log.

Two senders share one small interface, so the alerting logic never knows which is in use:

* ``ConsoleSender`` records the message in the application log instead of sending it. It
  costs nothing and needs no account, so development, automated tests and demonstrations
  use it. Termii offers no sandbox: every message it accepts is real and paid for.
* ``TermiiSender`` sends a real message through Termii's ``/api/sms/send`` endpoint.

``get_sms_sender`` picks the sender from the settings. Termii is used only when it is both
selected and fully configured, including a well-formed sender ID. Otherwise the console
sender is used and a warning says why, so a missing or placeholder value can never cause a
failed or unexpected real message.

Privacy: phone numbers are masked in every log line, and the API key is never logged.
"""

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("bloodlink.sms")

# Longest provider error text kept, matching the notification log's column.
_MAX_ERROR_LENGTH = 500


@dataclass(frozen=True)
class SmsResult:
    """What happened to one message.

    Attributes:
        ok: True when the provider accepted the message.
        message_id: The provider's identifier for the message, for tracing.
        error: Why it failed, when it did.
    """

    ok: bool
    message_id: str | None = None
    error: str | None = None


class SmsSender(Protocol):
    """Anything that can deliver a text message."""

    name: str

    def send(self, to: str, text: str) -> SmsResult:
        """Deliver ``text`` to the phone number ``to``. Must not raise."""
        ...


def mask_phone(phone: str) -> str:
    """Hide all but the last four digits, for log lines: ``+2348031234567`` -> ``*******4567``."""
    digits = phone.lstrip("+")
    return "*" * max(len(digits) - 4, 0) + digits[-4:]


def to_international(phone: str) -> str:
    """Convert a stored number to the digits-only international form Termii expects.

    ``+2348031234567`` and ``2348031234567`` become ``2348031234567``. A Nigerian number
    written in the local form, ``08031234567``, gains the country code. Anything else is
    passed on as digits, for the provider to accept or reject.
    """
    digits = phone.strip().lstrip("+")
    if digits.startswith("0") and len(digits) == 11:
        return "234" + digits[1:]
    return digits


class ConsoleSender:
    """Writes messages to the log instead of sending them."""

    name = "console"

    def send(self, to: str, text: str) -> SmsResult:
        logger.info("SMS (not sent, console sender) to %s: %s", mask_phone(to), text)
        return SmsResult(ok=True, message_id=f"console-{uuid4()}")


class TermiiSender:
    """Sends messages through Termii.

    Args:
        api_key: The account's secret key.
        base_url: The account-specific base address from the Termii dashboard.
        sender_id: The approved sender name.
        channel: ``dnd`` (transactional) or ``generic`` (promotional).
        timeout: Seconds to wait for Termii before giving up.
        client: An HTTP client to use; tests pass one with a mock transport.
    """

    name = "termii"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        sender_id: str,
        channel: str,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        # The dashboard shows the address either with or without the "/api" part.
        root = base_url.rstrip("/").removesuffix("/api")
        self._url = f"{root}/api/sms/send"
        self._sender_id = sender_id
        self._channel = channel
        self._client = client or httpx.Client(timeout=timeout)

    def send(self, to: str, text: str) -> SmsResult:
        payload = {
            "api_key": self._api_key,
            "to": to_international(to),
            "from": self._sender_id,
            "sms": text,
            "type": "plain",
            "channel": self._channel,
        }
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.HTTPError as exc:
            logger.warning(
                "Termii could not be reached for %s: %s", mask_phone(to), type(exc).__name__
            )
            return SmsResult(ok=False, error=f"Could not reach Termii ({type(exc).__name__}).")

        try:
            body = response.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}

        message_id = body.get("message_id_str") or body.get("message_id")
        if response.is_success and message_id:
            logger.info("SMS sent through Termii to %s", mask_phone(to))
            return SmsResult(ok=True, message_id=str(message_id))

        reason = str(body.get("message") or response.text or f"HTTP {response.status_code}")
        logger.warning(
            "Termii refused the message to %s (HTTP %s)", mask_phone(to), response.status_code
        )
        return SmsResult(ok=False, error=reason[:_MAX_ERROR_LENGTH])


def active_provider(settings: Settings | None = None) -> str:
    """The name of the sender that alerts will actually go through, without any warning."""
    config = settings or get_settings()
    return "termii" if config.sms_provider == "termii" and config.termii_ready else "console"


def get_sms_sender(settings: Settings | None = None) -> SmsSender:
    """Return the sender the settings ask for, falling back to the console when needed."""
    config = settings or get_settings()
    if config.sms_provider == "termii":
        if config.termii_ready:
            assert config.termii_api_key and config.termii_base_url and config.termii_sender_id
            return TermiiSender(
                api_key=config.termii_api_key,
                base_url=config.termii_base_url,
                sender_id=config.termii_sender_id,
                channel=config.termii_channel,
                timeout=config.sms_timeout_seconds,
            )
        missing = [
            name
            for name, present in (
                ("TERMII_API_KEY", bool(config.termii_api_key)),
                ("TERMII_BASE_URL", bool(config.termii_base_url)),
                ("TERMII_SENDER_ID (3 to 11 letters or digits)", config.termii_sender_id_valid),
            )
            if not present
        ]
        logger.warning(
            "SMS_PROVIDER is termii but %s is missing or invalid, so alerts are logged and "
            "not sent.",
            ", ".join(missing),
        )
    return ConsoleSender()
