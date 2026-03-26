# vz-sms

Send SMS messages from the command line using a Verizon USB730L LTE modem and AT commands.

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for package and virtual environment management
- A Verizon USB730L modem connected via USB

## Setup

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install pyserial

# Ensure your user has permission to access serial ports
sudo usermod -aG dialout $USER
# Log out and back in for group membership to take effect
```

## Usage

```bash
python vz-sms.py -d /dev/ttyUSB0 -n "+13159224851" -m "This is a test message. Hello from Python!!!"
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-d`, `--device` | `/dev/ttyUSB0` | Serial port for the modem |
| `-n`, `--number` | *(required)* | Destination phone number in E.164 format |
| `-m`, `--message` | *(required)* | SMS message body |

## Finding the Right Port

On Linux the modem exposes multiple virtual serial ports. The AT command port is typically `/dev/ttyUSB0`.

```bash
# List available ports after plugging in the modem
ls /dev/ttyUSB*

# Check kernel messages for port enumeration
dmesg | grep tty

# Confirm the modem is recognized
lsusb | grep Novatel
```

You can test the port interactively with `minicom`:

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
| `Unexpected response to 'AT'` | Wrong port or baud rate | Try a different `/dev/ttyUSBx` port |
| `No '>' prompt from modem` | Modem busy or stuck | Unplug/replug modem and retry |
| SMS sent but not received | Carrier filtering | Verify destination number; Verizon may filter A2P SMS |

## References

- [Novatel Wireless AT Command Reference v1.2](https://www.verizon.com/content/dam/support/pdf/verizon-usb730l-at-command-reference-guide.pdf)
- [Novatel Wireless Linux Integration Guide v1.1](https://www.verizon.com/content/dam/support/pdf/verizon-usb730l-integration-guide.pdf)
- [pyserial documentation](https://pyserial.readthedocs.io)
- 3GPP TS 27.005 — SMS AT commands standard
