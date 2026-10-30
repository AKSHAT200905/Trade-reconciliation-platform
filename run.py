import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WINDOWS = os.name == "nt"
VENV_PYTHON = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")
FRONTEND = ROOT / "frontend"
SERVICES = [
    {"name": "trade-service", "port": 8001, "db": "trades.db"},
    {"name": "recon-service", "port": 8002, "db": "recon.db"},
]
TRADE_URL = "http://127.0.0.1:8001"
RECON_URL = "http://127.0.0.1:8002"
WEB_URL = "http://localhost:5173"


def say(message):
    print(f"\n>>> {message}", flush=True)


def run(command, cwd=ROOT, env=None):
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"\nFailed: {' '.join(str(c) for c in command)}")
        sys.exit(1)


def check_tools():
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.")
        sys.exit(1)
    npm = shutil.which("npm")
    if npm is None:
        print("Node.js is not installed or npm is not on PATH. Install Node.js 20+ from nodejs.org.")
        sys.exit(1)
    return npm


def install(npm, force):
    stamp = VENV / ".installed"
    if force or not stamp.exists():
        if not VENV_PYTHON.exists():
            say("Creating Python virtual environment (first run only)")
            venv.create(VENV, with_pip=True)
        say("Installing Python packages (first run only)")
        run([str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"])
        for service in SERVICES:
            run([str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(ROOT / service["name"] / "requirements.txt")])
        stamp.write_text("ok")
    if force or not (FRONTEND / "node_modules").exists():
        say("Installing frontend packages (first run only)")
        run([npm, "install", "--no-audit", "--no-fund"], cwd=FRONTEND)


def service_env(service):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///./{service['db']}"
    env["TRADE_SERVICE_URL"] = TRADE_URL
    env["PYTHONUNBUFFERED"] = "1"
    return env


def migrate(reset):
    for service in SERVICES:
        folder = ROOT / service["name"]
        if reset:
            (folder / service["db"]).unlink(missing_ok=True)
        run([str(VENV_PYTHON), "-m", "alembic", "upgrade", "head"], cwd=folder, env=service_env(service))


def start(command, cwd, env):
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0
    return subprocess.Popen(command, cwd=cwd, env=env, creationflags=flags, start_new_session=not WINDOWS)


def wait_for(url, name, process, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if process.poll() is not None:
            print(f"\n{name} stopped unexpectedly. Scroll up for its error.")
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.5)
    print(f"\n{name} did not start within {seconds} seconds.")
    return False


def stop(processes):
    for process in processes:
        if process.poll() is not None:
            continue
        if WINDOWS:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    parser = argparse.ArgumentParser(description="Start TradeRecon locally with one command.")
    parser.add_argument("--reset", action="store_true", help="delete local data and start with empty databases")
    parser.add_argument("--reinstall", action="store_true", help="reinstall all packages")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args()

    npm = check_tools()
    install(npm, args.reinstall)
    say("Preparing databases")
    migrate(args.reset)

    processes = []
    try:
        say("Starting trade-service, recon-service and the dashboard")
        for service in SERVICES:
            processes.append(
                start(
                    [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(service["port"])],
                    ROOT / service["name"],
                    service_env(service),
                )
            )
        web_env = os.environ.copy()
        web_env["TRADE_SERVICE_URL"] = TRADE_URL
        web_env["RECON_SERVICE_URL"] = RECON_URL
        processes.append(start([npm, "run", "dev", "--", "--port", "5173", "--strictPort"], FRONTEND, web_env))

        checks = [
            (f"{TRADE_URL}/health", "trade-service", processes[0]),
            (f"{RECON_URL}/health", "recon-service", processes[1]),
            (WEB_URL, "dashboard", processes[2]),
        ]
        if not all(wait_for(url, name, process) for url, name, process in checks):
            stop(processes)
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"  TradeRecon is running:  {WEB_URL}")
        print(f"  API docs:               {TRADE_URL}/docs  and  {RECON_URL}/docs")
        print("  Press Ctrl+C to stop everything.")
        print("=" * 60 + "\n", flush=True)
        if not args.no_browser:
            webbrowser.open(WEB_URL)

        while all(process.poll() is None for process in processes):
            time.sleep(1)
        print("\nOne of the services stopped. Shutting down the rest.")
    except KeyboardInterrupt:
        print("\nStopping TradeRecon...")
    finally:
        stop(processes)
        print("Stopped.")


if __name__ == "__main__":
    main()
