import os

from nicemail import EmailClient

# Required environment variables:
#   NICEMAIL_EMAIL       - your Gmail address
#   NICEMAIL_CLIENT_ID   - OAuth 2.0 client ID (Desktop app type)
#   NICEMAIL_CLIENT_SECRET - OAuth 2.0 client secret
#   NICEMAIL_TO          - recipient address
# Optional:
#   NICEMAIL_PASSPHRASE


def main() -> None:
    sender = os.environ["NICEMAIL_EMAIL"]
    client_id = os.environ["NICEMAIL_CLIENT_ID"]
    client_secret = os.environ["NICEMAIL_CLIENT_SECRET"]
    recipient = os.environ["NICEMAIL_TO"]

    client = EmailClient(
        backend="google_api",
        google_api_config={
            "email_address": sender,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        passphrase=os.getenv("NICEMAIL_PASSPHRASE"),
    )

    # A browser will open automatically for authorization on the first run.
    # Subsequent runs reuse the cached token (or refresh it silently).
    client.send(
        to=recipient,
        subject="Hello from Nicemail",
        body_text="Sent via Google Gmail API.",
    )

    print("Send complete.")


if __name__ == "__main__":
    main()
