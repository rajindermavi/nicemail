import os

from nicemail import EmailClient

# Required environment variables:
#   NICEMAIL_EMAIL
#   NICEMAIL_CLIENT_ID
#   NICEMAIL_TO
# Optional:
#   NICEMAIL_PASSPHRASE
#   NICEMAIL_AUTHORITY (default: organization)

def main() -> None:
    sender = os.environ["NICEMAIL_EMAIL"]
    client_id = os.environ["NICEMAIL_CLIENT_ID"]
    recipient = os.environ["NICEMAIL_TO"]

    authority = os.getenv("NICEMAIL_AUTHORITY", "organization")

    client = EmailClient(
        backend="ms_graph",
        msal_config={
            "email_address": sender,
            "client_id": client_id,
            "authority": authority,
        },
        passphrase=os.getenv("NICEMAIL_PASSPHRASE"),
    )

    def show_device_code(flow: object) -> None:
        msg = flow.get("message") if isinstance(flow, dict) else str(flow)
        print(msg, flush=True)

    client.send(
        to=recipient,
        subject="Hello from Nicemail",
        body_text="Sent via Microsoft Graph.",
        show_message=show_device_code,
    )

    print("Send complete.")

if __name__ == "__main__":
    main()
