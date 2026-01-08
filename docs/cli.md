# CLI

Nicemail ships with a small CLI for quick dry-runs and one-off sends.

Dry-run output (no network):

    nicemail dry-run --to you@example.com --from me@example.com --subject "Hello" --body "Test" --out-dir ./dry_run_out

Real send (MS Graph):

    nicemail send --backend ms_graph --to you@example.com --subject "Hello" --body "Hello" --email me@example.com --client-id YOUR_CLIENT_ID
