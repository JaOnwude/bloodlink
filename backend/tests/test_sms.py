"""Tests of the SMS senders. No test here reaches Termii: HTTP is answered by a mock."""

import json
import logging

import httpx
import pytest

from app.core.config import Settings
from app.services.sms import (
    ConsoleSender,
    TermiiSender,
    active_provider,
    get_sms_sender,
    mask_phone,
    to_international,
)


def termii_with(handler) -> tuple[TermiiSender, list[httpx.Request]]:
    """A Termii sender whose HTTP calls go to ``handler`` instead of the network."""
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    sender = TermiiSender(
        api_key="test-key",
        base_url="https://example.api.termii.test/",
        sender_id="BloodLink",
        channel="dnd",
        timeout=5,
        client=client,
    )
    return sender, seen


def test_termii_receives_the_documented_payload() -> None:
    sender, seen = termii_with(
        lambda _: httpx.Response(200, json={"code": "ok", "message_id_str": "abc123"})
    )

    result = sender.send("+2348031234567", "Hello")

    assert result.ok is True
    assert result.message_id == "abc123"
    [request] = seen
    assert str(request.url) == "https://example.api.termii.test/api/sms/send"
    assert json.loads(request.content) == {
        "api_key": "test-key",
        "to": "2348031234567",
        "from": "BloodLink",
        "sms": "Hello",
        "type": "plain",
        "channel": "dnd",
    }


def test_a_base_url_that_already_ends_in_api_is_not_doubled() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message_id": 7}))
    )
    sender = TermiiSender(
        api_key="k",
        base_url="https://example.api.termii.test/api",
        sender_id="BloodLink",
        channel="dnd",
        timeout=5,
        client=client,
    )

    assert sender._url == "https://example.api.termii.test/api/sms/send"
    assert sender.send("2348031234567", "Hi").message_id == "7"


def test_a_refusal_is_reported_with_termiis_reason() -> None:
    sender, _ = termii_with(
        lambda _: httpx.Response(400, json={"message": "ApplicationSenderId not found"})
    )

    result = sender.send("+2348031234567", "Hello")

    assert result.ok is False
    assert result.error == "ApplicationSenderId not found"


def test_a_network_failure_is_reported_not_raised() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("too slow", request=request)

    sender, _ = termii_with(fail)

    result = sender.send("+2348031234567", "Hello")

    assert result.ok is False
    assert "ConnectTimeout" in result.error


def test_the_api_key_and_full_number_never_reach_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sender, _ = termii_with(lambda _: httpx.Response(500, text="server error"))

    with caplog.at_level(logging.INFO, logger="bloodlink.sms"):
        sender.send("+2348031234567", "Hello")

    assert "test-key" not in caplog.text
    assert "2348031234567" not in caplog.text
    assert "4567" in caplog.text


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("+2348031234567", "2348031234567"),
        ("2348031234567", "2348031234567"),
        ("08031234567", "2348031234567"),
        ("+447700900123", "447700900123"),
    ],
)
def test_numbers_are_converted_to_international_digits(stored: str, expected: str) -> None:
    assert to_international(stored) == expected


def test_phone_numbers_are_masked_for_logs() -> None:
    assert mask_phone("+2348031234567") == "*********4567"


def make_settings(**values) -> Settings:
    base = {
        "sms_provider": "termii",
        "termii_api_key": "k",
        "termii_base_url": "https://example.api.termii.test",
        "termii_sender_id": "BloodLink",
    }
    return Settings(**{**base, **values})


def test_termii_is_used_when_fully_configured() -> None:
    settings = make_settings()

    assert isinstance(get_sms_sender(settings), TermiiSender)
    assert active_provider(settings) == "termii"


@pytest.mark.parametrize(
    "sender_id",
    [None, "", "your-approved-sender-id", "AB", "WayTooLongName"],
)
def test_a_missing_or_malformed_sender_id_falls_back_to_the_console(
    sender_id: str | None, caplog: pytest.LogCaptureFixture
) -> None:
    settings = make_settings(termii_sender_id=sender_id)

    with caplog.at_level(logging.WARNING, logger="bloodlink.sms"):
        sender = get_sms_sender(settings)

    assert isinstance(sender, ConsoleSender)
    assert active_provider(settings) == "console"
    assert "TERMII_SENDER_ID" in caplog.text


def test_the_console_is_the_default() -> None:
    assert isinstance(get_sms_sender(Settings(sms_provider="console")), ConsoleSender)


def test_the_console_sender_logs_a_masked_number(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="bloodlink.sms"):
        result = ConsoleSender().send("+2348031234567", "Hello donor")

    assert result.ok is True
    assert result.message_id.startswith("console-")
    assert "Hello donor" in caplog.text
    assert "2348031234567" not in caplog.text
