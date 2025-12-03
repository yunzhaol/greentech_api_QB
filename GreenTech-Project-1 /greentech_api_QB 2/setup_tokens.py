#!/usr/bin/env python3
"""
Simple token setup - for when OAuth exchange fails
Just paste tokens from OAuth Playground
"""
import json
import pathlib
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("Quick Token Setup")
print("=" * 70)
print()
print("If OAuth setup failed, you can set tokens manually from OAuth Playground.")
print()

# Get tokens from user
print("Get tokens from: https://developer.intuit.com/v2/OAuth2Playground")
print()

access_token = input("Paste your ACCESS TOKEN: ").strip()
if not access_token:
    print("❌ Access token required")
    exit(1)

refresh_token = input("Paste your REFRESH TOKEN (optional, press Enter to skip): ").strip()
realm_id = input("Paste your REALM ID (optional, press Enter to skip): ").strip()

# Save access token to cache
cache_file = pathlib.Path(".token_cache.json")
cache_data = {
    "access_token": access_token,
    "expires_at": (datetime.now() + timedelta(seconds=3600)).isoformat()
}
cache_file.write_text(json.dumps(cache_data))
print()
print("✅ Access token saved to cache")

# Update .env if refresh token and realm_id provided
if refresh_token and realm_id:
    env_path = pathlib.Path(".env")
    if env_path.exists():
        import re
        env_content = env_path.read_text()
        
        # Update or add QBO_REFRESH_TOKEN
        if re.search(r'^QBO_REFRESH_TOKEN=', env_content, re.MULTILINE):
            env_content = re.sub(r'^QBO_REFRESH_TOKEN=.*$', f'QBO_REFRESH_TOKEN={refresh_token}', env_content, flags=re.MULTILINE)
        else:
            env_content += f'\nQBO_REFRESH_TOKEN={refresh_token}'
        
        # Update or add QBO_REALM_ID
        if re.search(r'^QBO_REALM_ID=', env_content, re.MULTILINE):
            env_content = re.sub(r'^QBO_REALM_ID=.*$', f'QBO_REALM_ID={realm_id}', env_content, flags=re.MULTILINE)
        else:
            env_content += f'\nQBO_REALM_ID={realm_id}'
        
        env_path.write_text(env_content)
        print("✅ Refresh token and Realm ID saved to .env")
    else:
        print("⚠️  .env file not found. Please add manually:")
        print(f"QBO_REFRESH_TOKEN={refresh_token}")
        print(f"QBO_REALM_ID={realm_id}")

print()
print("=" * 70)
print("✅ Setup Complete!")
print("=" * 70)
print()
print("You can now use the system:")
print("  python3 quickbooks_client.py")
print("  python3 create_estimate.py --json samples/quote_sample.json")
print()

