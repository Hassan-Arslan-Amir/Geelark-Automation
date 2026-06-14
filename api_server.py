"""
Unified GeeLark backend — Dashboard API + scheduled task worker.

Start everything with:
    python api_server.py

Set TASK_WORKER_ENABLED=0 to run the API only (no bot polling).
"""
import os
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from getDeviceIds import sync_devices_from_geelark
from task_worker import POLL_INTERVAL_SECONDS, run_worker_loop

load_dotenv()

app = Flask(__name__)

dashboard_origins = os.getenv(
    "DASHBOARD_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

CORS(app, origins=[origin.strip() for origin in dashboard_origins if origin.strip()])

_worker_stop = threading.Event()
_worker_thread: threading.Thread | None = None


def _worker_enabled() -> bool:
    return os.getenv("TASK_WORKER_ENABLED", "1").lower() not in ("0", "false", "no")


def start_task_worker() -> bool:
    """Start the scheduled-post worker in a background thread."""
    global _worker_thread

    if not _worker_enabled():
        print("⏸  Task worker disabled (TASK_WORKER_ENABLED=0)")
        return False

    if _worker_thread and _worker_thread.is_alive():
        return True

    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=run_worker_loop,
        args=(_worker_stop,),
        name="task-worker",
        daemon=True,
    )
    _worker_thread.start()
    return True


def stop_task_worker():
    _worker_stop.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)


@app.route("/api/health", methods=["GET"])
def health():
    worker_running = bool(_worker_thread and _worker_thread.is_alive())
    return jsonify({
        "ok": True,
        "worker": {
            "enabled": _worker_enabled(),
            "running": worker_running,
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        },
    })


@app.route("/api/sync-devices", methods=["POST"])
def sync_devices():
    try:
        result = sync_devices_from_geelark()
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


def main():
    port = int(os.getenv("API_PORT", "5001"))

    print("=" * 55)
    print("   GeeLark Unified Backend")
    print("=" * 55)

    start_task_worker()

    print(f"\n🌐 Dashboard API: http://127.0.0.1:{port}")
    print("   Endpoints:")
    print("     GET  /api/health")
    print("     POST /api/sync-devices")
    print("\n   Press Ctrl+C to stop.\n")

    try:
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    finally:
        stop_task_worker()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Backend stopped.")
