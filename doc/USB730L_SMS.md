# USB730L SMS via AT Commands — Implementation Reference

## Device Overview

- **Device**: Verizon Global Modem USB730L (Novatel Wireless)
- **AT Command Reference**: Novatel Wireless v1.2 (Aug 2017) — `USB730L-AT002`
- **Linux Integration Guide**: Novatel Wireless v1.1 — `USB730L-IG002`
- **Source docs**: `https://www.verizon.com/content/dam/support/pdf/`
  - `verizon-usb730l-at-command-reference-guide.pdf`
  - `verizon-usb730l-integration-guide.pdf`

---

## Linux Setup

### Port Detection

On Linux the modem enumerates as multiple virtual serial ports. The AT command port is typically **not** the first one:

```bash
# List available ports after plugging in USB
ls /dev/ttyUSB*

# Check kernel messages for port enumeration
dmesg | grep tty

# Confirm device is recognized
lsusb | grep Novatel
```

Typical port assignment:
| Port | Purpose |
|------|---------|
| `/dev/ttyUSB0` | Modem/AT command port (primary) |
| `/dev/ttyUSB1` | Secondary (may also accept AT commands) |
| `/dev/ttyUSB2` | Diagnostic / NMEA |

> **Note from integration guide**: The modem port should be `/dev/ttyUSB0`. Test interactively with PuTTY or `minicom` before scripting.

### Permissions

```bash
# Add user to dialout group to access serial ports without sudo
sudo usermod -aG dialout $USER
# Log out and back in for this to take effect

# Or set permissions directly for testing
sudo chmod 666 /dev/ttyUSB0
```

### Test with minicom

```bash
sudo apt install minicom
minicom -D /dev/ttyUSB0 -b 115200
# Type AT and press Enter — should respond OK
```

---

## Key AT Commands

> **WARNING (from Novatel docs)**: Do not use tab characters in AT command scripts.

All commands require a carriage return `\r` suffix. Responses are wrapped in `<CR><LF>`.

### Basic / Sanity Check

| Command | Description | Expected Response |
|---------|-------------|-------------------|
| `AT` | Attention / ping | `OK` |
| `AT+CGMI` | Manufacturer ID | `Novatel Wireless` |
| `AT+CGMM` | Model ID | `USB730L` |
| `AT+CGMR` | Firmware revision | version string |
| `AT+CIMI` | IMSI (SIM identity) | numeric string |
| `AT+CGSN` | IMEI | numeric string |
| `AT+CSQ` | Signal quality | `+CSQ: <rssi>,<ber>` |
| `AT+CREG?` | Network registration status | `+CREG: 0,1` (1=registered) |

### SIM & SMS Mode Setup

| Command | Description |
|---------|-------------|
| `AT+CPIN?` | Check SIM PIN status — should return `+CPIN: READY` |
| `AT+CMGF=1` | Set SMS text mode (vs PDU mode 0) — **use this for human-readable SMS** |
| `AT+CMGF?` | Query current SMS mode |
| `AT+CSCS="GSM"` | Set character set to GSM (default, 7-bit) |
| `AT+CSCS="UCS2"` | Set character set to Unicode (for non-ASCII) |

### Sending an SMS

```
AT+CMGS="<phone_number>"
```
After sending this command, the modem returns `>` as a prompt. Then send the message body followed by `Ctrl+Z` (ASCII `0x1A`) to transmit, or `ESC` (`0x1B`) to cancel.

Full sequence:
```
AT+CMGF=1\r          → OK
AT+CMGS="+1XXXXXXXXXX"\r  → >
Hello world\x1A       → +CMGS: <mr>\r\nOK
```

The `<mr>` in the response is the message reference number (confirmation).

### Reading Received SMS

| Command | Description |
|---------|-------------|
| `AT+CMGL="ALL"` | List all messages in storage |
| `AT+CMGL="REC UNREAD"` | List unread messages only |
| `AT+CMGR=<index>` | Read specific message by index |
| `AT+CMGD=<index>` | Delete message by index |
| `AT+CPMS?` | Query SMS storage (SIM vs modem memory) |

### Network / Status

| Command | Description |
|---------|-------------|
| `AT+COPS?` | Current operator name |
| `AT$NWNETTECH?` | Current network technology (LTE/3G/etc) — Novatel extension |
| `AT+VZWRSRP` | Verizon RSRP signal (LTE reference signal received power) |
| `AT+VZWRSRQ` | Verizon RSRQ signal quality |

---

## Python Implementation

### Dependencies

```bash
pip install pyserial
```

### Minimal SMS Send

```python
import serial
import time

MODEM_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

def send_at(ser, command, wait=0.5, expect="OK"):
    """Send an AT command and return the response."""
    ser.write((command + "\r").encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode(errors="ignore")
    if expect and expect not in response:
        raise RuntimeError(f"Unexpected response to '{command}': {repr(response)}")
    return response.strip()

def send_sms(to_number: str, message: str, port: str = MODEM_PORT):
    """Send an SMS via the USB730L modem."""
    with serial.Serial(port, BAUD_RATE, timeout=5) as ser:
        time.sleep(1)  # Allow port to settle

        send_at(ser, "AT")                  # Ping
        send_at(ser, "AT+CMGF=1")           # Text mode
        send_at(ser, 'AT+CSCS="GSM"')       # GSM charset

        # Send CMGS and wait for '>' prompt
        ser.write(f'AT+CMGS="{to_number}"\r'.encode())
        time.sleep(0.5)
        prompt = ser.read(ser.in_waiting).decode(errors="ignore")
        if ">" not in prompt:
            raise RuntimeError(f"No prompt received: {repr(prompt)}")

        # Send message body + Ctrl+Z
        ser.write(message.encode() + b"\x1A")
        time.sleep(4)  # Wait for send confirmation

        response = ser.read(ser.in_waiting).decode(errors="ignore")
        if "+CMGS:" not in response:
            raise RuntimeError(f"SMS send failed: {repr(response)}")
        return response

if __name__ == "__main__":
    result = send_sms("+1XXXXXXXXXX", "3")
    print("Sent:", result)
```

### Robust Version with Port Auto-Detection

```python
import serial
import serial.tools.list_ports
import time

def find_modem_port():
    """Try to auto-detect the USB730L AT command port."""
    candidates = [p.device for p in serial.tools.list_ports.comports()
                  if "USB" in (p.description or "").upper()
                  or "ttyUSB" in p.device]
    for port in candidates:
        try:
            with serial.Serial(port, 115200, timeout=2) as ser:
                ser.write(b"AT\r")
                time.sleep(0.3)
                resp = ser.read(ser.in_waiting).decode(errors="ignore")
                if "OK" in resp:
                    return port
        except Exception:
            continue
    raise RuntimeError("No responsive modem port found")

def check_signal(port: str = "/dev/ttyUSB0") -> str:
    """Return signal quality string."""
    with serial.Serial(port, 115200, timeout=5) as ser:
        ser.write(b"AT+CSQ\r")
        time.sleep(0.5)
        return ser.read(ser.in_waiting).decode(errors="ignore").strip()
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Permission denied: /dev/ttyUSB0` | Not in dialout group | `sudo usermod -aG dialout $USER` |
| `No such file or directory` | Wrong port or modem not enumerated | Check `dmesg`, try `/dev/ttyUSB1` |
| `AT` returns nothing | Wrong baud rate or wrong port | Try 9600, 57600, or a different ttyUSB port |
| `+CPIN: SIM PIN` | SIM is PIN-locked | Send `AT+CPIN="1234"` with your PIN |
| `+CREG: 0,0` | Not registered to network | Check signal `AT+CSQ`, may need antenna/location |
| `+CMS ERROR: 330` | SMS center not set | Set with `AT+CSCA="+1<smsc_number>"` — usually auto-configured on Verizon |
| `>` prompt never appears | Modem busy or wrong mode | Reset with `ATZ\r`, re-send CMGF=1 |
| SMS sent but not received | Message blocked by carrier | Verify destination number; Verizon may filter A2P SMS |

### Reset Modem State

```python
# Send before a sequence if the modem is in an unknown state
send_at(ser, "ATZ")    # Factory reset current profile
send_at(ser, "ATE0")   # Disable echo (cleaner responses)
```

---

## References

- AT Command Reference Guide v1.2: `verizon-usb730l-at-command-reference-guide.pdf`
- Linux Integration Guide v1.1: `verizon-usb730l-integration-guide.pdf`
- 3GPP TS 27.005 — SMS AT commands standard (covers CMGF, CMGS, CMGL)
- pyserial docs: `https://pyserial.readthedocs.io`
