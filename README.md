# vz-sms

Send SMS messages from the command line using either a **Verizon USB730L LTE modem** (AT commands over serial) or a **Cradlepoint IBR600 router** (REST API or SSH).

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for package and virtual environment management

## Setup

```bash
uv venv
source .venv/bin/activate

# USB730L mode (default)
uv pip install pyserial

# Cradlepoint REST API mode
uv pip install requests

# Cradlepoint SSH mode
uv pip install paramiko
```

For USB730L, your user must be in the `dialout` group:
```bash
sudo usermod -aG dialout $USER
# Log out and back in for group membership to take effect
```

## Usage

### USB730L (default)

```bash
python vz-sms.py -n "+13159224851" -m "Hello from Python!"
python vz-sms.py -d /dev/ttyUSB1 -n "+13159224851" -m "Hello from Python!"
```

### Cradlepoint IBR600 — REST API

```bash
python vz-sms.py --mode ibr600-api --router 192.168.0.1 \
    --user admin --password secret \
    -n "+13159224851" -m "Hello from Python!"
```

### Cradlepoint IBR600 — SSH

```bash
python vz-sms.py --mode ibr600-ssh --router 192.168.0.1 \
    --user admin --password secret \
    -n "+13159224851" -m "Hello from Python!"
```

## All Options

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `usb730l` | Send mode: `usb730l`, `ibr600-api`, `ibr600-ssh` |
| `-n`, `--number` | *(required)* | Destination phone number in E.164 format |
| `-m`, `--message` | *(required)* | SMS message body |
| `-d`, `--device` | `/dev/ttyUSB0` | Serial port (USB730L only) |
| `--router` | `192.168.0.1` | Router IP address (IBR600 only) |
| `--user` | `admin` | Router admin username (IBR600 only) |
| `--password` | | Router admin password (IBR600 only, required) |

## Finding the Right USB Port

The USB730L exposes multiple virtual serial ports on Linux. The AT command port is typically `/dev/ttyUSB0`.

```bash
ls /dev/ttyUSB*
dmesg | grep tty
lsusb | grep Novatel
```

Test interactively:
```bash
sudo apt install minicom
minicom -D /dev/ttyUSB0 -b 115200
# Type AT and press Enter — should respond OK
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Permission denied: /dev/ttyUSB0` | Not in dialout group | `sudo usermod -aG dialout $USER` |
| `No such file or directory` | Wrong port or modem not plugged in | Check `dmesg`, try `/dev/ttyUSB1` |
| `No '>' prompt from modem` | Modem busy or stuck | Unplug/replug modem and retry |
| `Could not connect to router` | Router unreachable | Check IP, try ping; verify HTTP/HTTPS setting |
| `401 Unauthorized` (IBR600 API) | Wrong credentials | Verify username/password in router web UI |
| SSH connection refused (IBR600) | SSH not enabled | Enable SSH in router admin interface |
| SMS sent but not received | Carrier filtering | Verify destination number; carriers may filter A2P SMS |

## References

- [Novatel AT Command Reference v1.2](https://www.verizon.com/content/dam/support/pdf/verizon-usb730l-at-command-reference-guide.pdf)
- [Novatel Linux Integration Guide v1.1](https://www.verizon.com/content/dam/support/pdf/verizon-usb730l-integration-guide.pdf)
- [pyserial documentation](https://pyserial.readthedocs.io)
- 3GPP TS 27.005 — SMS AT commands standard
