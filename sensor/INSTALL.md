# PTH Sensor — Installation

## Requirements

- Python 3.10+
- User must be in the `dialout` group for serial port access:
  ```bash
  sudo usermod -aG dialout $USER
  ```
  Log out and back in after running this.

## Install

```bash
pip install ./sensor
```

## Set up the systemd timer

```bash
pth-sensor install
```

This will:
- Create a config file at `~/.config/pth-sensor/config`
- Install and enable a systemd user timer

The default interval is every 5 minutes. To use a different interval:

```bash
pth-sensor install --interval 1min
```

## Configure

Edit `~/.config/pth-sensor/config` and set your server URL:

```
PTH_SERVER_URL=https://your-server.example.com
PTH_SERIAL_PORT=/dev/ttyACM0
PTH_POLL_INTERVAL_MS=1000
```

`PTH_POLL_INTERVAL_MS` controls the spacing between the 8 samples the sensor takes (and averages) on each run — it is unrelated to the timer interval set via `pth-sensor install --interval`, which controls how often `pth-sensor run` itself is invoked.

Changes take effect on the next timer tick — no need to restart the service.

## Useful commands

```bash
# Check timer status
systemctl --user status pth-sensor.timer

# View logs
journalctl --user -u pth-sensor.service -f

# Run once manually
pth-sensor run

# Stop and disable the timer
systemctl --user disable --now pth-sensor.timer
```
