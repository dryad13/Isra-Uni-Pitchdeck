"""Frozen entry point for the standalone Windows build.

Runs the FastAPI app via uvicorn in a background thread and, when frozen,
opens a native desktop window (pywebview). Closing the window stops the
server and exits the process.
"""

import multiprocessing
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request


def _setup_frozen_logging() -> None:
    """Windowed builds have no console — write startup output to a log file."""
    from app.paths import BASE_DIR, FROZEN

    if not FROZEN:
        return

    log_path = BASE_DIR / "data" / "omr.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    log_file.write(f"\n=== OMR start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log_file.flush()
    sys.stdout = log_file
    sys.stderr = log_file


_mutex_handle = None


def _acquire_single_instance_mutex() -> bool:
    """Return True if this process owns the single-instance mutex."""
    global _mutex_handle

    import ctypes

    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, True, "Global\\OMR_Desktop")
    if not handle:
        return False
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _mutex_handle = handle
    return True


def _wait_for_health(base_url: str, timeout: float = 120.0) -> bool:
    health_url = base_url.rstrip("/") + "/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.25)
    return False


def _run_uvicorn_thread(server) -> None:
    server.run()


def _run_native_window(url: str, server, server_thread: threading.Thread) -> None:
    import webview

    print("=" * 56)
    print("  On-Premises OMR System")
    print(f"  Console: {url}")
    print("  Close this window to quit the application.")
    print("=" * 56)

    if not _wait_for_health(url):
        print("ERROR: Server did not become ready in time.")
        server.should_exit = True
        server_thread.join(timeout=10)
        sys.exit(1)

    webview.create_window(
        "On-Premises OMR System",
        url,
        width=1280,
        height=800,
        min_size=(1024, 700),
    )
    webview.start()

    server.should_exit = True
    server_thread.join(timeout=10)


def _run_dev_server(host: str, port: int, app) -> None:
    import webbrowser

    import uvicorn

    url = f"http://{host}:{port}/"

    def _open_browser() -> None:
        time.sleep(2.0)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, args=(), daemon=True).start()

    print("=" * 56)
    print("  On-Premises OMR System (development)")
    print(f"  Console: {url}")
    print("  Press Ctrl+C to stop.")
    print("=" * 56)

    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    import uvicorn

    from app.config import get_config
    from app.main import app
    from app.paths import FROZEN, ensure_writable_dirs

    _setup_frozen_logging()
    ensure_writable_dirs()

    if FROZEN and sys.platform == "win32":
        if not _acquire_single_instance_mutex():
            print("OMR is already running.")
            sys.exit(0)

    cfg = get_config()
    host = cfg.server.host
    port = cfg.server.port
    url = f"http://{host}:{port}/"

    if FROZEN:
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server_thread = threading.Thread(
            target=_run_uvicorn_thread,
            args=(server,),
            daemon=True,
        )
        server_thread.start()
        _run_native_window(url, server, server_thread)
        return

    _run_dev_server(host, port, app)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
