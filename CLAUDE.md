# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

Use `uv` for all Python package and virtual environment management — never `pip`, `python -m venv`, or `poetry`.

```bash
uv venv
source .venv/bin/activate
uv pip install pyserial
```

## Running the Script

```bash
python vz-sms.py -d /dev/ttyUSB0 -n "+1XXXXXXXXXX" -m "Message text"
```

The `-d` flag defaults to `/dev/ttyUSB0` if omitted.

## Architecture

The entire project is a single script (`vz-sms.py`) with no external dependencies beyond `pyserial`.

**AT command flow** (`vz-sms.py`):
1. `main()` parses CLI args and calls `send_sms()`
2. `send_sms()` opens the serial port, runs the setup sequence (`ATZ` → `ATE0` → `AT` → `AT+CMGF=1` → `AT+CSCS="GSM"`), then issues `AT+CMGS="<number>"` and waits for the `>` prompt
3. The message body + `\x1A` (Ctrl+Z) is written to trigger transmission; `+CMGS:` in the response confirms success
4. `send_at()` is a low-level helper: writes `command\r`, sleeps, reads available bytes, and raises `RuntimeError` if the expected string (default `"OK"`) is absent

**Key timing constants** (top of file): `SETTLE_TIME`, `CMD_WAIT`, `SEND_WAIT` — adjust if the modem is slow to respond.

## Hardware Notes

- The modem exposes multiple `/dev/ttyUSBx` ports; the AT command port is typically `/dev/ttyUSB0`
- User must be in the `dialout` group: `sudo usermod -aG dialout $USER`
- Full AT command reference: `doc/USB730L_SMS.md`
