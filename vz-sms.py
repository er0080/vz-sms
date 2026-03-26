#!/usr/bin/env python3
"""
vz-sms.py — Send SMS from the command line via a Verizon USB730L LTE modem.

Usage:
    python vz-sms.py -d /dev/ttyUSB0 -n "+13159224851" -m "Hello from Python!"
"""

import argparse
import sys
import time

import serial


BAUD_RATE = 115200
SETTLE_TIME = 1.0     # seconds after opening port
CMD_WAIT = 0.5        # seconds after sending a command
SEND_WAIT = 5.0       # seconds to wait for +CMGS confirmation


def send_at(ser: serial.Serial, command: str, wait: float = CMD_WAIT, expect: str = "OK") -> str:
    """Send an AT command and return the response, raising on unexpected output."""
    ser.write((command + "\r").encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode(errors="ignore")
    if expect and expect not in response:
        raise RuntimeError(f"Unexpected response to '{command}': {repr(response)}")
    return response.strip()


def send_sms(port: str, number: str, message: str) -> str:
    """
    Open the modem serial port and send an SMS to number.
    Returns the modem's confirmation response string.
    """
    with serial.Serial(port, BAUD_RATE, timeout=5) as ser:
        time.sleep(SETTLE_TIME)

        send_at(ser, "ATZ")             # Reset modem state
        send_at(ser, "ATE0")            # Disable echo for cleaner responses
        send_at(ser, "AT")              # Sanity check
        send_at(ser, "AT+CMGF=1")       # Text mode
        send_at(ser, 'AT+CSCS="GSM"')   # GSM 7-bit character set

        # Initiate send — modem replies with '>' prompt
        ser.write(f'AT+CMGS="{number}"\r'.encode())
        time.sleep(CMD_WAIT)
        prompt = ser.read(ser.in_waiting).decode(errors="ignore")
        if ">" not in prompt:
            raise RuntimeError(f"No '>' prompt from modem after CMGS: {repr(prompt)}")

        # Send message body followed by Ctrl+Z (0x1A) to transmit
        ser.write(message.encode() + b"\x1A")
        time.sleep(SEND_WAIT)

        response = ser.read(ser.in_waiting).decode(errors="ignore")
        if "+CMGS:" not in response:
            raise RuntimeError(f"SMS send failed — no +CMGS confirmation: {repr(response)}")

        return response.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send an SMS via a Verizon USB730L LTE modem using AT commands."
    )
    parser.add_argument(
        "-d", "--device",
        default="/dev/ttyUSB0",
        metavar="PORT",
        help="Serial port for the modem (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "-n", "--number",
        required=True,
        metavar="PHONE",
        help="Destination phone number in E.164 format, e.g. +13159224851",
    )
    parser.add_argument(
        "-m", "--message",
        required=True,
        metavar="TEXT",
        help="SMS message body",
    )
    args = parser.parse_args()

    try:
        result = send_sms(args.device, args.number, args.message)
        print(f"SMS sent successfully.\n{result}")
        return 0
    except serial.SerialException as exc:
        print(f"Serial port error: {exc}", file=sys.stderr)
        print("Check that the modem is connected and you have permission to access the port.", file=sys.stderr)
        print("  sudo usermod -aG dialout $USER  (then log out/in)", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Modem error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
