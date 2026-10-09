"""Local-only TTN webhook ingress and offline tools for Thermo-IoT.

This is a reference integration, not a public Internet deployment stack.
Terminate TLS and configure inbound allowlisting upstream when deployed.
"""

import argparse
from dataclasses import asdict
from functools import partial
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys

from .telemetry import TelemetryService, TelemetryStore, UplinkValidationError


MAX_BODY_BYTES = 65536


def _reject_duplicate_keys(pairs):
    obj = {}
    for name, value in pairs:
        if name in obj:
            raise ValueError("Duplicate JSON key")
        obj[name] = value
    return obj


def _reject_nonfinite(value):
    raise ValueError("Non-finite JSON number")


def _parse_json(raw: bytes) -> object:
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite,
    )


class _WebhookHandler(BaseHTTPRequestHandler):
    """Handler factory injects application service and secret through constructor."""

    def __init__(self, *args, service: TelemetryService, token: str, **kwargs):
        self._service = service
        self._token = token
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """No device identifiers, auth headers or payloads in HTTP logs."""

    def _json(self, status: int, value: dict) -> None:
        encoded = json.dumps(value, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"state": "ready", "mode": "reference"})
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/ttn/uplink":
            self._json(404, {"error": "not_found"})
            return
        auth = self.headers.get("Authorization", "")
        expected = "Bearer " + self._token
        if not hmac.compare_digest(auth.encode("utf-8", "replace"), expected.encode("utf-8")):
            self._json(401, {"error": "unauthorized"})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self._json(400, {"error": "chunked_upload_not_supported"})
            return
        media_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if media_type != "application/json":
            self._json(415, {"error": "content_type"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._json(411, {"error": "content_length_required"})
            return
        if length < 1:
            self._json(400, {"error": "empty_body"})
            return
        if length > MAX_BODY_BYTES:
            self._json(413, {"error": "body_too_large"})
            return
        raw = self.rfile.read(length)
        if len(raw) != length:
            self._json(400, {"error": "truncated_body"})
            return
        try:
            event = _parse_json(raw)
            receipt = self._service.process(event)
        except (ValueError, UnicodeError, UplinkValidationError):
            self._json(400, {"error": "invalid_uplink"})
            return
        self._json(201 if receipt.inserted else 200, receipt.to_dict())


def build_server(
    host: str, port: int, service: TelemetryService, *, token: str
) -> ThreadingHTTPServer:
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("A random webhook bearer token of at least 32 characters is required")
    if not 0 <= port <= 65535:
        raise ValueError("Invalid HTTP port")
    server = ThreadingHTTPServer((host, port), partial(_WebhookHandler, service=service, token=token))
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Thermo-IoT reference telemetry ingress")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Validate and save one TTN v3 JSON uplink")
    ingest.add_argument("--db", required=True)
    ingest.add_argument("--file", required=True)

    report = commands.add_parser("report", help="Report device history summary from local SQLite")
    report.add_argument("--db", required=True)
    report.add_argument("--app", required=True)
    report.add_argument("--device", required=True)

    serve = commands.add_parser("serve", help="Serve authenticated TTN webhooks over local HTTP")
    serve.add_argument("--db", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    try:
        store = TelemetryStore(args.db)
        if args.command == "ingest":
            with open(args.file, "rb") as stream:
                raw = stream.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                raise ValueError("Uplink JSON is too large")
            receipt = TelemetryService(store).process(_parse_json(raw))
            print(json.dumps(receipt.to_dict(), indent=2))
            return 0
        if args.command == "report":
            print(json.dumps(store.summary(args.app, args.device), indent=2))
            return 0
        if args.command == "serve":
            token = os.environ.get("THERMO_IOT_WEBHOOK_TOKEN", "")
            with build_server(args.host, args.port, TelemetryService(store), token=token) as server:
                print(f"Thermo-IoT local webhook bound to {server.server_address}", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return 0
    except (OSError, ValueError, UplinkValidationError) as exc:
        print(f"Thermo-IoT: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
