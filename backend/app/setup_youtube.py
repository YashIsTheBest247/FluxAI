"""One-time YouTube token generator for Flux operators.

Run this once on the host where the backend lives:

    cd backend
    python -m app.setup_youtube

It will open a browser tab, ask you to sign in with the Google account that owns the channel
you want renders published to, and persist a refresh token at `secrets/youtube_token.json`.

From then on, every generated video auto-publishes to that channel — no per-user sign-in needed.

Prerequisite: a 'Desktop app' OAuth client JSON saved at `secrets/youtube_client_secret.json`.
"""
from pathlib import Path
import sys

from .config import settings
from .services.youtube_service import _get_service, TokenMissing


def main() -> int:
    secrets_path = Path(settings.youtube_client_secrets)
    token_path = Path(settings.youtube_token_file)

    print(f"  client secrets : {secrets_path}")
    print(f"  token file     : {token_path}")
    print()

    if not secrets_path.exists():
        print(f"  client secrets missing.")
        print()
        print(f"  1. Open https://console.cloud.google.com/apis/credentials")
        print(f"  2. Create an OAuth client of type 'Desktop app'")
        print(f"  3. Download the JSON and save it at:")
        print(f"       {secrets_path}")
        print(f"  4. Run this script again.")
        return 1

    print("opening browser for Google sign-in...")
    print("pick the account that owns the YouTube channel Flux should publish to.\n")

    try:
        service = _get_service(allow_interactive=True)
    except TokenMissing as e:
        print(f"  FAILED: {e}")
        return 1
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return 1

    try:
        resp = service.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if items:
            ch = items[0]
            sn = ch["snippet"]
            st = ch.get("statistics", {})
            print(f"  Connected channel : {sn.get('title')}")
            print(f"  Channel ID        : {ch['id']}")
            print(f"  Subscribers       : {st.get('subscriberCount', '—')}")
            print(f"  Videos            : {st.get('videoCount', '—')}")
        print()
        print(f"  Token saved at    : {token_path}")
        print(f"  All future renders will auto-publish to this channel.")
        return 0
    except Exception as e:
        print(f"  Token saved, but couldn't fetch channel info: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
