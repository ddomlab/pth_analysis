import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "pth-sensor"
CONFIG_FILE = CONFIG_DIR / "config"

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_POLL_INTERVAL_MS = 1000


def _default_device_id() -> str:
    return socket.gethostname()


CONFIG_TEMPLATE = f"""\
PTH_SERVER_URL=https://your-server.example.com
PTH_SERIAL_PORT={DEFAULT_SERIAL_PORT}
PTH_POLL_INTERVAL_MS={DEFAULT_POLL_INTERVAL_MS}
# PTH_DEVICE_ID={_default_device_id()}
"""


@dataclass
class Config:
    server_url: str
    serial_port: str = DEFAULT_SERIAL_PORT
    poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS
    device_id: str = field(default_factory=_default_device_id)


def _parse_env_file(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def load_config() -> Config:
    """Load settings from the config file, with PTH_* environment variables taking precedence."""
    values: dict[str, str] = {}
    if CONFIG_FILE.exists():
        values.update(_parse_env_file(CONFIG_FILE))
    values.update((k, v) for k, v in os.environ.items() if k.startswith("PTH_"))

    server_url = values.get("PTH_SERVER_URL")
    if not server_url:
        raise RuntimeError(f"PTH_SERVER_URL is not set. Add it to {CONFIG_FILE}")

    return Config(
        server_url=server_url,
        serial_port=values.get("PTH_SERIAL_PORT", DEFAULT_SERIAL_PORT),
        poll_interval_ms=int(values.get("PTH_POLL_INTERVAL_MS", DEFAULT_POLL_INTERVAL_MS)),
        device_id=values.get("PTH_DEVICE_ID", _default_device_id()),
    )
