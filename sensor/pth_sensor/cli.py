import argparse
import grp
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import CONFIG_DIR, CONFIG_FILE, CONFIG_TEMPLATE

SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

SERVICE_NAME = "pth-sensor.service"
TIMER_NAME = "pth-sensor.timer"


def _exec_path() -> str:
    candidate = shutil.which("pth-sensor")
    if candidate:
        return candidate
    return str(Path(sys.executable).parent / "pth-sensor")


def _service_content(exec_path: str) -> str:
    return f"""\
[Unit]
Description=PTH Sensor data collector
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={exec_path} run
StandardOutput=journal
StandardError=journal
"""


def _timer_content(interval: str) -> str:
    return f"""\
[Unit]
Description=Run PTH sensor collector on a fixed interval

[Timer]
OnBootSec=30
OnUnitActiveSec={interval}
AccuracySec=1s

[Install]
WantedBy=timers.target
"""


def cmd_run(_args):
    from .post_pth import post_pth
    post_pth()


def cmd_install(args):
    exec_path = _exec_path()

    # Create config file with defaults if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(CONFIG_TEMPLATE)
        print(f"Created config template at {CONFIG_FILE}")
        print(f"  -> Edit PTH_SERVER_URL before the service will work correctly.\n")
    else:
        print(f"Config already exists at {CONFIG_FILE}, leaving it unchanged.\n")

    # Write systemd unit files
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    service_path = SYSTEMD_USER_DIR / SERVICE_NAME
    timer_path = SYSTEMD_USER_DIR / TIMER_NAME

    service_path.write_text(_service_content(exec_path))
    timer_path.write_text(_timer_content(args.interval))
    print(f"Wrote {service_path}")
    print(f"Wrote {timer_path}\n")

    # Reload and enable
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", TIMER_NAME], check=True)
    print(f"\nTimer enabled. Check status with:")
    print(f"  systemctl --user status {TIMER_NAME}")
    print(f"  journalctl --user -u {SERVICE_NAME} -f\n")

    # Warn if dialout group membership is missing
    try:
        dialout_members = grp.getgrnam("dialout").gr_mem
        if os.getlogin() not in dialout_members:
            print("WARNING: your user is not in the 'dialout' group.")
            print("  Serial port access will fail. Fix with:")
            print(f"  sudo usermod -aG dialout {os.getlogin()}")
            print("  Then log out and back in.\n")
    except KeyError:
        pass


def main():
    parser = argparse.ArgumentParser(prog="pth-sensor")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Read sensor and post data once")

    install_p = sub.add_parser("install", help="Install and enable systemd timer")
    install_p.add_argument(
        "--interval",
        default="5min",
        help="Timer interval (e.g. 1min, 5min, 1h). Default: 5min",
    )

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "install":
        cmd_install(args)
