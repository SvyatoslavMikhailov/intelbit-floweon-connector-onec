"""Тесты OneCWebhookReceiver: HMAC, replay, dedup, 4 типа событий."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path

import fakeredis
import pytest

from intelbit_river_connector_onec.webhooks import OneCWebhookReceiver, WebhookSignatureError

FIXTURES = Path(__file__).parent / "fixtures" / "onec-mocks" / "webhooks"
SECRET = "test-webhook-secret-32-bytes-long"


def _make_receiver(**kwargs: object) -> OneCWebhookReceiver:
    config = {"webhook_secret": SECRET, "replay_window_sec": 300}
    config.update(kwargs)  # type: ignore[arg-type]
    return OneCWebhookReceiver(config)


def _make_signature(body: bytes, timestamp: int | None = None) -> str:
    t = timestamp if timestamp is not None else int(time.time())
    payload = f"{t}.".encode() + body
    sig = hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


class TestVerifySignature:
    def test_valid_signature_passes(self) -> None:
        body = b'{"event_type": "catalog.updated", "event_id": "x"}'
        sig = _make_signature(body)
        receiver = _make_receiver()
        receiver.verify_signature({"X-Signature": sig}, body)  # не должно бросать

    def test_missing_header_raises(self) -> None:
        receiver = _make_receiver()
        with pytest.raises(WebhookSignatureError, match="отсутствует"):
            receiver.verify_signature({}, b"body")

    def test_wrong_hash_raises(self) -> None:
        body = b'{"event_type": "catalog.updated"}'
        t = int(time.time())
        receiver = _make_receiver()
        with pytest.raises(WebhookSignatureError, match="HMAC"):
            receiver.verify_signature({"X-Signature": f"t={t},v1=badhash"}, body)

    def test_replay_attack_old_timestamp(self) -> None:
        body = b'{"event_type": "catalog.updated"}'
        # Подпись с timestamp 600 секунд назад (> 300s окно)
        old_ts = int(time.time()) - 600
        sig = _make_signature(body, timestamp=old_ts)
        receiver = _make_receiver()
        with pytest.raises(WebhookSignatureError, match="Replay"):
            receiver.verify_signature({"X-Signature": sig}, body)

    def test_replay_attack_future_timestamp(self) -> None:
        body = b'{"event_type": "catalog.updated"}'
        future_ts = int(time.time()) + 600
        sig = _make_signature(body, timestamp=future_ts)
        receiver = _make_receiver()
        with pytest.raises(WebhookSignatureError, match="Replay"):
            receiver.verify_signature({"X-Signature": sig}, body)

    def test_lowercase_header_key_works(self) -> None:
        body = b'{"event_type": "stock.updated", "event_id": "y"}'
        sig = _make_signature(body)
        receiver = _make_receiver()
        receiver.verify_signature({"x-signature": sig}, body)  # не должно бросать

    def test_invalid_timestamp_raises(self) -> None:
        receiver = _make_receiver()
        with pytest.raises(WebhookSignatureError, match="целым"):
            receiver.verify_signature({"X-Signature": "t=notanumber,v1=abc"}, b"body")


class TestDeduplicate:
    def test_first_event_returns_true(self) -> None:
        redis = fakeredis.FakeRedis()
        receiver = _make_receiver()
        assert receiver.deduplicate("evt-unique-001", redis) is True

    def test_duplicate_event_returns_false(self) -> None:
        redis = fakeredis.FakeRedis()
        receiver = _make_receiver()
        receiver.deduplicate("evt-dup-001", redis)
        assert receiver.deduplicate("evt-dup-001", redis) is False

    def test_different_events_both_new(self) -> None:
        redis = fakeredis.FakeRedis()
        receiver = _make_receiver()
        assert receiver.deduplicate("evt-a", redis) is True
        assert receiver.deduplicate("evt-b", redis) is True


class TestParseEvent:
    def test_parse_catalog_updated(self) -> None:
        body = (FIXTURES / "catalog_updated.json").read_bytes()
        receiver = _make_receiver()
        event = receiver.parse_event(body)
        assert event["event_type"] == "catalog.updated"
        assert event["event_id"] == "evt-cat-0001"

    def test_parse_stock_updated(self) -> None:
        body = (FIXTURES / "stock_updated.json").read_bytes()
        receiver = _make_receiver()
        event = receiver.parse_event(body)
        assert event["event_type"] == "stock.updated"

    def test_parse_price_updated(self) -> None:
        body = (FIXTURES / "price_updated.json").read_bytes()
        receiver = _make_receiver()
        event = receiver.parse_event(body)
        assert event["event_type"] == "price.updated"

    def test_parse_order_status_changed(self) -> None:
        body = (FIXTURES / "order_status_changed.json").read_bytes()
        receiver = _make_receiver()
        event = receiver.parse_event(body)
        assert event["event_type"] == "order.status.changed"
        assert event["data"]["new_status"] == "Согласован"

    def test_unsupported_event_type_raises(self) -> None:
        body = json.dumps({"event_type": "unknown.event", "event_id": "x"}).encode()
        receiver = _make_receiver()
        with pytest.raises(ValueError, match="Неподдерживаемый"):
            receiver.parse_event(body)

    def test_invalid_json_raises(self) -> None:
        receiver = _make_receiver()
        with pytest.raises(ValueError, match="JSON"):
            receiver.parse_event(b"not json at all {{{")
