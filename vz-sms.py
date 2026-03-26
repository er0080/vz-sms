#!/usr/bin/env python3
"""
vz-sms.py — Send SMS from the command line via a USB modem or Cradlepoint router.

Modes:
  usb730l      (default) Verizon USB730L modem via serial AT commands
  ibr600-api   Cradlepoint IBR600 via local REST API (HTTP Digest Auth)
  ibr600-ssh   Cradlepoint IBR600 via SSH CLI `sms` command

Usage:
    # USB730L (default)
    python vz-sms.py -n "+13159224851" -m "Hello!"
    python vz-sms.py -d /dev/ttyUSB0 -n "+13159224851" -m "Hello!"

    # Cradlepoint REST API
    python vz-sms.py --mode ibr600-api --router 192.168.0.1 --user admin --password secret \
        -n "+13159224851" -m "Hello!"

    # Cradlepoint SSH
    python vz-sms.py --mode ibr600-ssh --router 192.168.0.1 --user admin --password secret \
        -n "+13159224851" -m "Hello!"
"""

import argparse
import sys
import time

# ---------------------------------------------------------------------------
# USB730L constants
# ---------------------------------------------------------------------------
BAUD_RATE   = 115200
SETTLE_TIME = 1.0    # seconds after opening serial port
CMD_WAIT    = 0.5    # seconds after each AT command
SEND_WAIT   = 5.0    # seconds to wait for +CMGS confirmation

# ---------------------------------------------------------------------------
# IBR600 constants
# ---------------------------------------------------------------------------
IBR600_API_PATH = "/api/control/sms"
IBR600_TIMEOUT  = 10  # seconds for HTTP / SSH operations


# ===========================================================================
# USB730L — AT command helpers
# ===========================================================================

def send_at(ser, command: str, wait: float = CMD_WAIT, expect: str = "OK") -> str:
    """Send an AT command and return the response, raising on unexpected output."""
    ser.write((command + "\r").encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode(errors="ignore")
    if expect and expect not in response:
        raise RuntimeError(f"Unexpected response to '{command}': {repr(response)}")
    return response.strip()


def send_sms_usb730l(port: str, number: str, message: str) -> str:
    """Send an SMS via the Verizon USB730L modem using AT commands."""
    import serial  # imported here so ibr600 modes don't require pyserial

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


# ===========================================================================
# Cradlepoint IBR600 — REST API
# ===========================================================================

def send_sms_ibr600_api(router: str, user: str, password: str,
                         number: str, message: str) -> str:
    """Send an SMS via the IBR600 local REST API (HTTP Digest Auth)."""
    import requests
    from requests.auth import HTTPDigestAuth
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Try HTTPS first; fall back to HTTP if a connection error occurs
    for scheme in ("https", "http"):
        url = f"{scheme}://{router}{IBR600_API_PATH}"
        payload = {"data": {"phone": number, "message": message}}
        try:
            response = requests.post(
                url,
                json=payload,
                auth=HTTPDigestAuth(user, password),
                verify=False,
                timeout=IBR600_TIMEOUT,
            )
            response.raise_for_status()
            return str(response.json())
        except requests.exceptions.SSLError:
            continue  # try plain HTTP
        except requests.exceptions.ConnectionError:
            if scheme == "https":
                continue
            raise

    raise RuntimeError(f"Could not connect to router at {router} via HTTPS or HTTP")


# ===========================================================================
# Cradlepoint IBR600 — SSH CLI
# ===========================================================================

def send_sms_ibr600_ssh(router: str, user: str, password: str,
                         number: str, message: str) -> str:
    """Send an SMS via the IBR600 SSH CLI `sms` command."""
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=router,
            username=user,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=IBR600_TIMEOUT,
        )
        # Single-quote the message; escape any embedded single quotes
        safe_message = message.replace("'", "'\\''")
        _, stdout, stderr = client.exec_command(f"sms {number} '{safe_message}'")
        output = stdout.read().decode().strip()
        error  = stderr.read().decode().strip()
        if error:
            raise RuntimeError(f"Router returned error: {error}")
        return output or "OK"
    finally:
        client.close()


# ===========================================================================
# CLI
# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send an SMS via a USB730L modem or Cradlepoint IBR600 router.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["usb730l", "ibr600-api", "ibr600-ssh"],
        default="usb730l",
        help="Send mode (default: usb730l)",
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

    # USB730L options
    usb_group = parser.add_argument_group("USB730L options")
    usb_group.add_argument(
        "-d", "--device",
        default="/dev/ttyUSB0",
        metavar="PORT",
        help="Serial port for the modem (default: /dev/ttyUSB0)",
    )

    # IBR600 options
    ibr_group = parser.add_argument_group("IBR600 options")
    ibr_group.add_argument(
        "--router",
        default="192.168.0.1",
        metavar="IP",
        help="Router IP address (default: 192.168.0.1)",
    )
    ibr_group.add_argument(
        "--user",
        default="admin",
        metavar="USER",
        help="Router admin username (default: admin)",
    )
    ibr_group.add_argument(
        "--password",
        metavar="PASS",
        help="Router admin password",
    )

    args = parser.parse_args()

    # Validate IBR600 options
    if args.mode in ("ibr600-api", "ibr600-ssh") and not args.password:
        parser.error(f"--password is required for --mode {args.mode}")

    try:
        if args.mode == "usb730l":
            result = send_sms_usb730l(args.device, args.number, args.message)
        elif args.mode == "ibr600-api":
            result = send_sms_ibr600_api(
                args.router, args.user, args.password, args.number, args.message
            )
        else:  # ibr600-ssh
            result = send_sms_ibr600_ssh(
                args.router, args.user, args.password, args.number, args.message
            )

        print(f"SMS sent successfully.\n{result}")
        return 0

    except Exception as exc:  # pylint: disable=broad-except
        # Provide mode-specific hints alongside the error message
        print(f"Error: {exc}", file=sys.stderr)
        if args.mode == "usb730l":
            print("Check that the modem is connected and you are in the 'dialout' group.", file=sys.stderr)
            print("  sudo usermod -aG dialout $USER  (then log out/in)", file=sys.stderr)
        elif args.mode == "ibr600-api":
            print(f"Check that the router at {args.router} is reachable and credentials are correct.", file=sys.stderr)
        elif args.mode == "ibr600-ssh":
            print(f"Check that SSH is enabled on {args.router} and credentials are correct.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
