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

    print("This will prompt for device code if needed.")

    client.send(
        to=recipient,
        subject="Hello from Nicemail",
        body_text="Sent via Microsoft Graph.",
    )

    print("Send complete.")

if __name__ == "__main__":
    main()
