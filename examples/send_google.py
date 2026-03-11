import os

from nicemail import EmailClient

# Required environment variables:
#   NICEMAIL_EMAIL
#   NICEMAIL_CLIENT_ID
#   NICEMAIL_TO
# Optional:
#   NICEMAIL_CLIENT_SECRET
#   NICEMAIL_PASSPHRASE


def main() -> None:
    sender = os.environ["NICEMAIL_EMAIL"]
    client_id = os.environ["NICEMAIL_CLIENT_ID"]
    recipient = os.environ["NICEMAIL_TO"]

    client = EmailClient(
        backend="google_api",
        google_api_config={
            "email_address": sender,
            "client_id": client_id,
            "client_secret": os.getenv("NICEMAIL_CLIENT_SECRET"),
        },
        passphrase=os.getenv("NICEMAIL_PASSPHRASE"),
    )

    def show_device_code(flow: object) -> None:
        if isinstance(flow, dict):
            url = (
                flow.get("verification_uri_complete")
                or flow.get("verification_url")
                or flow.get("verification_uri")
            )
            code = flow.get("user_code")
            if url and code:
                print(f"Visit {url} and enter code: {code}", flush=True)
                return
        print(str(flow), flush=True)

    client.send(
        to=recipient,
        subject="Hello from Nicemail",
        body_text="Sent via Google Gmail API.",
        show_message=show_device_code,
    )

    print("Send complete.")


if __name__ == "__main__":
    main()
