from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an authorized Gmail token JSON for Lambda email alerts."
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Path to the OAuth client JSON downloaded from Google Cloud Console.",
    )
    parser.add_argument(
        "--output",
        default="gmail_token.json",
        help="Where to write the authorized-user token JSON.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local callback port. Use 0 to pick a free port automatically.",
    )
    parser.add_argument(
        "--print-terraform-var",
        action="store_true",
        help="Print a terraform -var argument containing the generated token JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    credentials_path = Path(args.credentials).expanduser()
    output_path = Path(args.output).expanduser()

    if not credentials_path.exists():
        raise SystemExit(f"OAuth client file not found: {credentials_path}")

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=args.port,
        authorization_prompt_message="Open this URL to authorize Gmail sending:\n{url}",
        success_message="Gmail authorization complete. You can close this browser tab.",
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )

    token_info = json.loads(credentials.to_json())
    token_info["scopes"] = SCOPES
    output_path.write_text(json.dumps(token_info, indent=2), encoding="utf-8")

    print(f"Wrote Gmail authorized-user token to {output_path}")
    if not token_info.get("refresh_token"):
        print("Warning: no refresh_token was returned. Revoke the app grant and run again with consent.")

    if args.print_terraform_var:
        compact = json.dumps(token_info, separators=(",", ":"))
        print("\nTerraform argument:")
        print(f"-var={shlex.quote('gmail_token_json=' + compact)}")


if __name__ == "__main__":
    main()
