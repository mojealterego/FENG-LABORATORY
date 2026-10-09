"""Read-only localhost telemetry UI using the gateway's SQLite storage format.

A laboratory monitoring prototype, not a production OT/SCADA control service.
All database connections use SQLite mode=ro; mutating HTTP verbs are disabled.
"""

import argparse
from contextlib import closing
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"


class DashboardRepository:
    """SQLite read-only repository with bounded per-device history."""

    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        if not self.path.is_file():
            raise ValueError("A previously created telemetry SQLite database is required")
        self.uri = self.path.resolve().as_uri() + "?mode=ro"
        try:
            with closing(self._open()) as conn:
                conn.execute("SELECT app_id, device_id, state FROM readings LIMIT 0")
        except sqlite3.DatabaseError as exc:
            raise ValueError("File is not a compatible gateway telemetry database") from exc

    def _open(self) -> sqlite3.Connection:
        return sqlite3.connect(self.uri, uri=True, timeout=5)

    def devices(self) -> list[dict]:
        with closing(self._open()) as conn:
            records = conn.execute("""
                SELECT app_id, device_id, COUNT(*) AS total,
                       SUM(CASE WHEN state='anomaly_candidate' THEN 1 ELSE 0 END)
                           AS candidate_anomalies,
                       MAX(received_at) AS latest_received_at
                FROM readings GROUP BY app_id, device_id
                ORDER BY app_id, device_id LIMIT 1000
            """).fetchall()
        return [dict(zip(("app_id", "device_id", "total", "candidate_anomalies",
                          "latest_received_at"), row)) for row in records]

    @staticmethod
    def _identifier(value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError("Invalid application or device identifier")
        return value

    def history(self, app_id: str, device_id: str, *, limit: int = 100) -> list[dict]:
        self._identifier(app_id)
        self._identifier(device_id)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("History limit must be from 1 to 200")
        with closing(self._open()) as conn:
            rows = conn.execute("""
                SELECT received_at, temperature_centi_c, capacitor_mv,
                       teg_power_uw, state, frame_counter
                FROM readings WHERE app_id=? AND device_id=?
                ORDER BY received_at DESC, id DESC LIMIT ?
            """, (app_id, device_id, limit)).fetchall()
        return [{
            "received_at": row[0],
            "temperature_c": row[1] / 100,
            "capacitor_voltage_v": row[2] / 1000,
            "teg_power_uw": row[3],
            "state": row[4],
            "frame_counter": row[5],
        } for row in reversed(rows)]


class _DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, repository: DashboardRepository, **kwargs):
        self._repository = repository
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Avoid logging operational identifiers and raw telemetry."""

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        request = urlsplit(self.path)
        static = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
        }
        if request.path in static and not request.query:
            name, media = static[request.path]
            body = files("thermo_iot").joinpath("static", name).read_bytes()
            self._send(200, body, media)
            return
        if request.path == "/api/devices" and not request.query:
            try:
                self._json(200, {
                    "devices": self._repository.devices(),
                    "warning": "Laboratory data; no certified fault detection",
                })
            except sqlite3.DatabaseError:
                self._json(503, {"error": "database_unavailable"})
            return
        if request.path == "/api/history":
            try:
                query = parse_qs(request.query, strict_parsing=True, keep_blank_values=True)
                if set(query) != {"app", "device", "limit"} or any(len(v) != 1 for v in query.values()):
                    raise ValueError("Exactly one app, device and limit are required")
                value = query["limit"][0]
                if not value.isascii() or not value.isdecimal():
                    raise ValueError("Invalid history limit")
                history = self._repository.history(
                    query["app"][0], query["device"][0], limit=int(value)
                )
            except ValueError:
                self._json(400, {"error": "invalid_query"})
                return
            except sqlite3.DatabaseError:
                self._json(503, {"error": "database_unavailable"})
                return
            self._json(200, {"history": history})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self):
        self._json(405, {"error": "read_only"})

    def do_PUT(self):
        self._json(405, {"error": "read_only"})

    def do_DELETE(self):
        self._json(405, {"error": "read_only"})


def build_server(host: str, port: int, repository: DashboardRepository) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("The demo dashboard can only bind to localhost")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("Invalid dashboard port")
    server = ThreadingHTTPServer((host, port), partial(_DashboardHandler, repository=repository))
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only local Thermo-IoT laboratory dashboard")
    parser.add_argument("--db", required=True, help="SQLite created by thermo_iot.gateway")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    try:
        with build_server(args.host, args.port, DashboardRepository(args.db)) as server:
            print(f"Local Thermo-IoT dashboard: http://{args.host}:{server.server_port}/", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except (OSError, ValueError) as exc:
        print(f"Dashboard: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
