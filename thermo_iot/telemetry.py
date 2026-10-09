"""The Things Stack v3 uplink adapter and transactional local evidence store.

Reference protocol and analysis only. No calibrated sensor, radio modem,
operator installation, cloud platform or leak detection is implied.
"""

import base64
import binascii
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
import sqlite3
import struct
from collections.abc import Mapping
from pathlib import Path

from .anomaly import DetectionPolicy, detect_temperature_anomaly


_FORMAT = struct.Struct("<BhHHB")
_VERSION = 1
_FPORT = 10
_UNAVAILABLE_TEG = 65535
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$"
)


class UplinkValidationError(ValueError):
    """A payload or trusted integration envelope violates the local contract."""


@dataclass(frozen=True)
class SensorSample:
    temperature_centi_c: int
    capacitor_mv: int
    teg_power_uw: int | None
    flags: int

    @property
    def temperature_c(self) -> float:
        return self.temperature_centi_c / 100.0

    @property
    def capacitor_voltage_v(self) -> float:
        return self.capacitor_mv / 1000.0


@dataclass(frozen=True)
class Uplink:
    app_id: str
    device_id: str
    session_key_id: str
    frame_counter: int
    received_at: str
    sample: SensorSample


@dataclass(frozen=True)
class IngestReceipt:
    app_id: str
    device_id: str
    frame_counter: int
    received_at: str
    inserted: bool
    state: str
    temperature_c: float
    capacitor_voltage_v: float
    teg_power_uw: int | None

    def to_dict(self) -> dict:
        return asdict(self)


def _as_int(value: object, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise UplinkValidationError(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _validate_sample(sample: SensorSample) -> None:
    _as_int(sample.temperature_centi_c, "temperature_centi_c", -4000, 15000)
    _as_int(sample.capacitor_mv, "capacitor_mv", 0, 5500)
    if sample.teg_power_uw is not None:
        _as_int(sample.teg_power_uw, "teg_power_uw", 0, 65534)
    _as_int(sample.flags, "flags", 0, 255)


def encode_frame(
    temperature_centi_c: int, capacitor_mv: int,
    teg_uw: int | None, flags: int = 0
) -> bytes:
    """Eight-byte reference payload: version, temp cC, cap mV, TEG uW, flags.

    The absence of TEG measurement is encoded as the sentinel value 0xffff.
    This is an application protocol; no device firmware is yet implemented.
    """
    sample = SensorSample(temperature_centi_c, capacitor_mv, teg_uw, flags)
    _validate_sample(sample)
    return _FORMAT.pack(
        _VERSION, sample.temperature_centi_c, sample.capacitor_mv,
        sample.teg_power_uw if sample.teg_power_uw is not None else _UNAVAILABLE_TEG,
        sample.flags,
    )


def decode_frame(raw: bytes) -> SensorSample:
    if not isinstance(raw, bytes) or len(raw) != _FORMAT.size:
        raise UplinkValidationError("Expected exactly 8 binary payload bytes")
    version, temperature, capacitor, teg, flags = _FORMAT.unpack(raw)
    if version != _VERSION:
        raise UplinkValidationError(f"Unsupported protocol version {version}")
    sample = SensorSample(
        temperature_centi_c=temperature,
        capacitor_mv=capacitor,
        teg_power_uw=None if teg == _UNAVAILABLE_TEG else teg,
        flags=flags,
    )
    _validate_sample(sample)
    return sample


def _object(value: object, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise UplinkValidationError(f"{label} must be an object")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise UplinkValidationError(f"Invalid {label}")
    return value


def _received_timestamp(value: object) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value):
        raise UplinkValidationError("received_at must be a timezone-aware RFC3339 timestamp")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("no timezone")
        return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except ValueError as exc:
        raise UplinkValidationError("Invalid received_at timestamp") from exc


def parse_ttn_uplink(event: Mapping) -> Uplink:
    """Decode an already-authenticated The Things Stack v3 application uplink.

    TTN must terminate the LoRaWAN MIC/crypto; do not expose this parser as
    unauthenticated public traffic. Reject encrypted skip-payload-crypto data.
    """
    event = _object(event, "event")
    end_ids = _object(event.get("end_device_ids"), "end_device_ids")
    app_ids = _object(end_ids.get("application_ids"), "application_ids")
    message = _object(event.get("uplink_message"), "uplink_message")
    app_id = _identifier(app_ids.get("application_id"), "application_id")
    device_id = _identifier(end_ids.get("device_id"), "device_id")
    session = message.get("session_key_id")
    if not isinstance(session, str) or not 1 <= len(session) <= 2048:
        raise UplinkValidationError("session_key_id is required for safe frame counter deduplication")
    counter = _as_int(message.get("f_cnt"), "f_cnt", 0, 4294967295)
    if _as_int(message.get("f_port"), "f_port", 0, 255) != _FPORT:
        raise UplinkValidationError("Unexpected application FPort")
    if "app_s_key" in message:
        raise UplinkValidationError("Encrypted frm_payload is not supported")
    encoded = message.get("frm_payload")
    if not isinstance(encoded, str) or len(encoded) > 64:
        raise UplinkValidationError("Invalid frm_payload length")
    try:
        raw = base64.b64decode(encoded, validate=True)
        if base64.b64encode(raw).decode("ascii") != encoded:
            raise ValueError("Non-canonical base64")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise UplinkValidationError("frm_payload must be canonical base64") from exc
    sample = decode_frame(raw)
    return Uplink(
        app_id=app_id, device_id=device_id,
        session_key_id=session, frame_counter=counter,
        received_at=_received_timestamp(event.get("received_at")),
        sample=sample,
    )


class TelemetryStore:
    """Local SQLite store; one connection per operation and bounded per-device baseline."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) == ":memory:":
            raise ValueError("Use a persistent SQLite path for the per-operation connection store")
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    session_key_id TEXT NOT NULL,
                    frame_counter INTEGER NOT NULL,
                    received_at TEXT NOT NULL,
                    temperature_centi_c INTEGER NOT NULL,
                    capacitor_mv INTEGER NOT NULL,
                    teg_power_uw INTEGER,
                    flags INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    UNIQUE(app_id, device_id, session_key_id, frame_counter)
                )"""
            )
            conn.execute(
                """CREATE INDEX IF NOT EXISTS readings_history_idx
                ON readings(app_id, device_id, received_at DESC, id DESC)"""
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(str(self.db_path), timeout=5.0)
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _receipt(uplink: Uplink, inserted: bool, state: str) -> IngestReceipt:
        return IngestReceipt(
            app_id=uplink.app_id,
            device_id=uplink.device_id,
            frame_counter=uplink.frame_counter,
            received_at=uplink.received_at,
            inserted=inserted,
            state=state,
            temperature_c=uplink.sample.temperature_c,
            capacitor_voltage_v=uplink.sample.capacitor_voltage_v,
            teg_power_uw=uplink.sample.teg_power_uw,
        )

    def ingest(self, uplink: Uplink, policy: DetectionPolicy = DetectionPolicy()) -> IngestReceipt:
        policy.validate()
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            identity = (uplink.app_id, uplink.device_id, uplink.session_key_id, uplink.frame_counter)
            existing = conn.execute(
                """SELECT received_at, temperature_centi_c, capacitor_mv, teg_power_uw, flags
                   FROM readings WHERE app_id=? AND device_id=? AND session_key_id=?
                   AND frame_counter=?""", identity
            ).fetchone()
            if existing is not None:
                if existing != (
                    uplink.received_at, uplink.sample.temperature_centi_c,
                    uplink.sample.capacitor_mv, uplink.sample.teg_power_uw, uplink.sample.flags
                ):
                    raise UplinkValidationError("Conflicting payload for an existing LoRaWAN frame")
                return self._receipt(uplink, False, "duplicate")
            latest = conn.execute(
                """SELECT received_at FROM readings
                   WHERE app_id=? AND device_id=?
                   ORDER BY received_at DESC, id DESC LIMIT 1""",
                (uplink.app_id, uplink.device_id),
            ).fetchone()
            if latest and uplink.received_at < latest[0]:
                state = "out_of_order"
            else:
                historical_rows = conn.execute(
                    """SELECT temperature_centi_c FROM readings
                       WHERE app_id=? AND device_id=? AND received_at<=?
                       AND state <> 'out_of_order'
                       ORDER BY received_at DESC, id DESC LIMIT 50""",
                    (uplink.app_id, uplink.device_id, uplink.received_at),
                ).fetchall()
                historical_values = [row[0] / 100 for row in historical_rows]
                state = detect_temperature_anomaly(
                    historical_values, uplink.sample.temperature_c, policy
                ).state
            conn.execute(
                """INSERT INTO readings
                   (app_id, device_id, session_key_id, frame_counter, received_at,
                    temperature_centi_c, capacitor_mv, teg_power_uw, flags, state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*identity, uplink.received_at, uplink.sample.temperature_centi_c,
                 uplink.sample.capacitor_mv, uplink.sample.teg_power_uw, uplink.sample.flags, state),
            )
            return self._receipt(uplink, True, state)

    def summary(self, app_id: str, device_id: str) -> dict:
        _identifier(app_id, "application_id")
        _identifier(device_id, "device_id")
        with self._connection() as conn:
            totals = conn.execute(
                """SELECT COUNT(*), COUNT(CASE WHEN state='anomaly_candidate' THEN 1 END)
                   FROM readings WHERE app_id=? AND device_id=?""",
                (app_id, device_id),
            ).fetchone()
            latest = conn.execute(
                """SELECT received_at, temperature_centi_c, capacitor_mv, state
                   FROM readings WHERE app_id=? AND device_id=?
                   ORDER BY received_at DESC, id DESC LIMIT 1""",
                (app_id, device_id),
            ).fetchone()
        return {
            "app_id": app_id,
            "device_id": device_id,
            "total": totals[0],
            "candidate_anomalies": totals[1],
            "latest": None if latest is None else {
                "received_at": latest[0],
                "temperature_c": latest[1] / 100,
                "capacitor_voltage_v": latest[2] / 1000,
                "state": latest[3],
            },
        }


class TelemetryService:
    """Application boundary for ingestion; retains no credentials in reports."""

    def __init__(self, store: TelemetryStore, policy: DetectionPolicy = DetectionPolicy()) -> None:
        policy.validate()
        self.store = store
        self.policy = policy

    def process(self, event: Mapping) -> IngestReceipt:
        return self.store.ingest(parse_ttn_uplink(event), self.policy)
