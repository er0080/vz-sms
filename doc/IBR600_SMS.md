# Cradlepoint IBR600 — Sending SMS Programmatically (Python)

The IBR600 exposes a CLI over SSH that includes a built-in `sms` command:

```
sms <address> <message> [port]
```

Examples:
```bash
ssh admin@192.168.0.1 "sms 5551234567 'Hello from CLI'"
ssh admin@192.168.0.1 "sms +15551234567 'International number'"
```

---

## Python Implementation (using Paramiko)

```python
import paramiko

ROUTER_IP   = "192.168.0.1"
ROUTER_PORT = 22
ROUTER_USER = "admin"
ROUTER_PASS = "your_password_here"

def send_sms_ssh(phone_number: str, message: str) -> str:
    """
    Send an SMS via the IBR600 SSH CLI.

    Args:
        phone_number: Destination number, e.g. "5551234567" or "+15551234567"
        message:      Message body text

    Returns:
        stdout output from the router command.
    """
    client = paramiko.SSHClient()
    # IBR600 will have an unknown host key on first connection — adjust policy as needed
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=ROUTER_IP,
            port=ROUTER_PORT,
            username=ROUTER_USER,
            password=ROUTER_PASS,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        # Escape embedded single quotes
        safe_message = message.replace("'", "'\\''")
        command = f"sms {phone_number} '{safe_message}'"
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode().strip()
        error  = stderr.read().decode().strip()

        if error:
            raise RuntimeError(f"Router returned error: {error}")

        return output

    finally:
        client.close()


if __name__ == "__main__":
    result = send_sms_ssh("+15551234567", "Hello from Python over SSH!")
    print(result)
```

> **Security note:** `AutoAddPolicy()` automatically trusts the router's host key on first connection. For a more secure setup, capture the router's host key once and save it to a `known_hosts` file, then use `client.load_host_keys("known_hosts")` instead.

---

## Dependencies

```bash
uv pip install paramiko
```

---

## Tips & Troubleshooting

- **Message quoting:** Single quotes inside the message body are automatically escaped (`'\''`) so they don't break the shell command.
- **Phone number format:** Accepts numbers with or without a leading `+` for international format. Domestic numbers can be passed as plain digits (e.g. `5551234567`).
- **Firmware changes:** Cradlepoint has indicated that newer NCOS firmware versions may restrict outbound SMS. If SMS stops working after a firmware update, check the router changelog to confirm the feature is still present.
- **Timeout:** Set a reasonable `timeout` on the connection to avoid indefinite hangs if the router is unreachable.
