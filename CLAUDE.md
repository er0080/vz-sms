# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

Use `uv` for all Python package and virtual environment management — never `pip`, `python -m venv`, or `poetry`.

```bash
uv venv
source .venv/bin/activate
uv pip install pyserial          # USB730L mode
uv pip install requests          # ibr600-api mode
uv pip install paramiko          # ibr600-ssh mode
```

## Running the Script

```bash
# USB730L (default)
python vz-sms.py -n "+1XXXXXXXXXX" -m "Message text"
python vz-sms.py -d /dev/ttyUSB0 -n "+1XXXXXXXXXX" -m "Message text"

# Cradlepoint IBR600 — REST API
python vz-sms.py --mode ibr600-api --router 192.168.0.1 --user admin --password secret \
    -n "+1XXXXXXXXXX" -m "Message text"

# Cradlepoint IBR600 — SSH
python vz-sms.py --mode ibr600-ssh --router 192.168.0.1 --user admin --password secret \
    -n "+1XXXXXXXXXX" -m "Message text"
```

## Architecture

Single script (`vz-sms.py`), no package structure. Each send mode is an independent function; `main()` dispatches to the right one based on `--mode`.

**USB730L flow** (`send_sms_usb730l`):
1. Opens serial port, waits `SETTLE_TIME` for the port to stabilize
2. Runs setup sequence: `ATZ` → `ATE0` → `AT` → `AT+CMGF=1` → `AT+CSCS="GSM"`
3. Issues `AT+CMGS="<number>"`, waits for `>` prompt
4. Writes message body + `\x1A` (Ctrl+Z) to transmit; confirms `+CMGS:` in response
5. `send_at()` is the low-level helper: write → sleep → read → assert expected string

**IBR600 REST API flow** (`send_sms_ibr600_api`):
- `POST /api/control/sms` with `{"data": {"phone": ..., "message": ...}}`
- HTTP Digest Auth; tries HTTPS first, falls back to HTTP on SSL error
- Router uses a self-signed cert — `verify=False` is intentional

**IBR600 SSH flow** (`send_sms_ibr600_ssh`):
- Connects via Paramiko; runs `sms <number> '<message>'`
- Single quotes in the message are escaped with `'\\''`
- Uses `AutoAddPolicy` (trusts unknown host keys on first connect)

**Key timing constants** (USB730L, top of file): `SETTLE_TIME`, `CMD_WAIT`, `SEND_WAIT` — adjust if the modem is slow to respond.

## Hardware Notes

- USB730L: AT command port is typically `/dev/ttyUSB0`; user must be in `dialout` group
- IBR600: REST API endpoint and JSON payload may vary by firmware — verify via browser DevTools if sends fail
- Full reference docs: `doc/USB730L_SMS.md`, `doc/IBR600_SMS.md`
