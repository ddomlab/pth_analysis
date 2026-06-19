# PTH Sensor — Installation

## Requirements

- Python 3.10+
- User must be in the `dialout` group for serial port access:
  ```bash
  sudo usermod -aG dialout $USER
  ```
  Log out and back in after running this.

## Install

To install the sensor software without git-cloning (recommended), simply run:

```bash
pip install "git+https://github.com/ddomlab/pth_analysis.git#subdirectory=sensor"
```

Alternatively, clone the git repository and pip install from there:

```bash
git clone https://github.com/ddomlab/pth_analysis.git
```
```bash
pip install pth_analysis/sensor
``` 

## Set up the systemd timer

```bash
pth-sensor install
```

This will:
- Create a config file at `~/.config/pth-sensor/config`
- Install and enable a systemd user timer

The default interval is every 15 minutes. To use a different interval:

```bash
pth-sensor install --interval 1min
```

## Stable serial port (recommended)

`/dev/ttyACM*` (`/dev/ttyACM0`, `/dev/ttyACM1`, etc.) is assigned by USB enumeration order, which can shift after a reboot or if the sensor ends up in a different USB port — when that happens, `PTH_SERIAL_PORT` silently points at the wrong (or a nonexistent) device. A udev rule pins a fixed symlink to the sensor's hardware serial number, so the path stays correct no matter how it's enumerated.

1. With the sensor plugged in, find its serial device address (likely `/dev/ttyACM0`)
  * Find relevant devices: `ls /dev/tty*`, look for names like `ttyACM0`, `ttyACM1`, `ttyUSB0`
  * Confirm the device's identity
    ```bash
    udevadm info -q property -n /dev/ttyACM1 | grep -E 'ID_SERIAL'
    ```
    This should return something like `ID_SERIAL=Dracal_technologies_inc._VCP-PTH200...`

2. Now having confirmed its identity, look up its vendor ID, product ID, and serial number:
   ```bash
   udevadm info -a -n /dev/ttyACM0 | grep -E 'idVendor|idProduct|serial' | head -3
   ```
3. Create `/etc/udev/rules.d/99-pth-sensor.rules`, filling in the values from step 2:
   ```
   SUBSYSTEM=="tty", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", ATTRS{serial}=="ZZZZZZ", SYMLINK+="ttyPTH"
   ```
4. Reload udev and reconnect the sensor:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```
   Unplug and replug the sensor (or reboot) if `/dev/ttyPTH` doesn't appear right away.
5. Point `PTH_SERIAL_PORT` at `/dev/ttyPTH` instead of `/dev/ttyACM*` (see Configure below).

Every sensor has its own unique serial number, so this rule has to be generated per device — don't reuse another setup's vendor/product/serial values.

## Configure

Edit `~/.config/pth-sensor/config` and set your server URL:

```
PTH_SERVER_URL=http://your-server.example.com
PTH_SERIAL_PORT=/dev/ttyPTH
PTH_POLL_INTERVAL_MS=1000
PTH_DEVICE_ID=greenhouse-1
```

`PTH_DEVICE_ID` identifies this Pi to the server when multiple sensors are posting to the same server, and is stored alongside every reading. Defaults to the Pi's hostname if not set.

`PTH_SERIAL_PORT` can be `/dev/ttyACM*` directly, but `/dev/ttyPTH` (see Stable serial port above) won't break if the port number shifts.

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
