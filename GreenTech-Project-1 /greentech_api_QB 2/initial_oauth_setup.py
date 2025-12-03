#!/usr/bin/env python3
"""
GreenTech Painting - Initial OAuth 2.0 Setup
Run this ONCE to get your initial refresh token.

This script creates a temporary local server to automatically handle
the OAuth redirect callback from QuickBooks/Intuit.
"""
import os
import webbrowser
import requests
import threading
import time
import pathlib
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
CLIENT_ID = os.getenv("QBO_CLIENT_ID")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
QBO_MODE = os.getenv("QBO_MODE", "sandbox")

# Redirect URI - Use Intuit's default (no admin access needed)
# Alternative: Use local server if you have admin access to add redirect URI
USE_LOCAL_SERVER = False  # Set to True if you can add http://localhost:8080/callback to Intuit app

if USE_LOCAL_SERVER:
    OAUTH_CALLBACK_PORT = 8080
    REDIRECT_URI = f"http://localhost:{OAUTH_CALLBACK_PORT}/callback"
else:
    # Intuit's default redirect URI (works without admin access)
    REDIRECT_URI = "https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl"

# OAuth endpoints
AUTH_ENDPOINT = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Global variables for OAuth callback
oauth_result = {
    "code": None,
    "realm_id": None,
    "state": None,
    "error": None,
    "received": False
}
flask_app = None
server_thread = None

def create_callback_server():
    """Creates a Flask server to handle OAuth callback"""
    global flask_app
    
    flask_app = Flask(__name__)
    
    @flask_app.route('/callback')
    def oauth_callback():
        """Handles the OAuth redirect callback from QuickBooks"""
        global oauth_result
        
        # Get parameters from URL
        code = request.args.get('code')
        realm_id = request.args.get('realmId')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            oauth_result["error"] = error
            oauth_result["received"] = True
            return """
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Failed</h1>
                <p>Error: {}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """.format(error), 400
        
        if code and realm_id:
            oauth_result["code"] = code
            oauth_result["realm_id"] = realm_id
            oauth_result["state"] = state
            oauth_result["received"] = True
            
            return """
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authorization Successful!</h1>
                <p>You have successfully authorized the application.</p>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """, 200
        else:
            oauth_result["error"] = "Missing code or realmId in callback"
            oauth_result["received"] = True
            return """
            <html>
            <head><title>Authorization Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Error</h1>
                <p>Missing required parameters in callback URL.</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """, 400
    
    return flask_app

def start_callback_server():
    """Starts the callback server in a separate thread"""
    global flask_app, server_thread
    
    flask_app = create_callback_server()
    
    def run_server():
        flask_app.run(host='127.0.0.1', port=OAUTH_CALLBACK_PORT, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    print(f"✅ Local callback server started on {REDIRECT_URI}")

def wait_for_callback(timeout=300):
    """Waits for OAuth callback to be received"""
    global oauth_result
    
    print("⏳ Waiting for authorization callback...")
    print(f"   (Timeout: {timeout} seconds)")
    
    start_time = time.time()
    while not oauth_result["received"]:
        if time.time() - start_time > timeout:
            return False, "Timeout waiting for callback"
        time.sleep(0.5)
    
    if oauth_result["error"]:
        return False, oauth_result["error"]
    
    if not oauth_result["code"] or not oauth_result["realm_id"]:
        return False, "Missing code or realmId in callback"
    
    return True, None

def validate_config():
    """Validates that required config is set"""
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ ERROR: QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in .env file")
        print()
        print("Steps to fix:")
        print("1. Copy .env.example to .env")
        print("2. Go to https://developer.intuit.com")
        print("3. Create an app and get your Client ID and Client Secret")
        print("4. Add them to your .env file")
        print()
        print("⚠️  IMPORTANT: In your Intuit Developer app settings, add this redirect URI:")
        print(f"   {REDIRECT_URI}")
        return False
    return True

def generate_auth_url():
    """Generates the OAuth authorization URL"""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": "security_token_greentech_12345"
    }
    
    url_params = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{AUTH_ENDPOINT}?{url_params}"

def exchange_code_for_tokens(auth_code):
    """Exchanges authorization code for access and refresh tokens"""
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
    }
    
    print("\n🔄 Exchanging authorization code for tokens...")
    
    response = requests.post(
        TOKEN_ENDPOINT,
        headers=headers,
        data=data,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    
    if response.status_code == 200:
        token_data = response.json()
        
        # Handle both camelCase and snake_case response formats
        # Intuit API sometimes returns camelCase (refreshToken, accessToken)
        # Normalize to snake_case for consistency
        if 'refreshToken' in token_data and 'refresh_token' not in token_data:
            token_data['refresh_token'] = token_data.pop('refreshToken')
        if 'accessToken' in token_data and 'access_token' not in token_data:
            token_data['access_token'] = token_data.pop('accessToken')
        
        return token_data
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Provide helpful error message
        if "invalid_client" in response.text:
            print()
            print("=" * 70)
            print("⚠️  WORKAROUND: Use OAuth Playground")
            print("=" * 70)
            print()
            print("The authorization code might be from OAuth Playground with different credentials.")
            print("Here's how to get tokens:")
            print()
            print("1. Go to: https://developer.intuit.com/v2/OAuth2Playground")
            print("2. Use your CLIENT_ID and CLIENT_SECRET from .env file")
            print("3. Get authorization code (you already have it)")
            print("4. Exchange for tokens in the playground")
            print("5. Copy the tokens and run:")
            print("   python3 set_token_cache.py")
            print()
            print("Or update your .env file with:")
            print("   QBO_REFRESH_TOKEN=<refresh_token_from_playground>")
            print("   QBO_REALM_ID=<realm_id>")
            print()
        
        return None

def main():
    """Main OAuth setup flow"""
    global oauth_result
    
    print("=" * 70)
    print("GreenTech Painting - QuickBooks OAuth 2.0 Setup")
    print("=" * 70)
    print()
    print(f"Mode: {QBO_MODE.upper()}")
    print()
    
    # Validate configuration
    if not validate_config():
        return
    
    print("✅ Configuration validated")
    print()
    
    # Check which mode we're using
    if USE_LOCAL_SERVER:
        # Local server mode - requires redirect URI to be added
        print("⚠️  IMPORTANT: Before proceeding, make sure you've added this redirect URI")
        print("   to your Intuit Developer app settings:")
        print()
        print(f"   {REDIRECT_URI}")
        print()
        print("   Steps:")
        print("   1. Go to https://developer.intuit.com")
        print("   2. Select your app")
        print("   3. Go to 'Keys & OAuth' section")
        print("   4. Add the redirect URI above to 'Redirect URIs'")
        print("   5. Click 'Save'")
        print()
        response = input("Have you added the redirect URI to your Intuit app? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Please add the redirect URI first, then run this script again.")
            return
        
        print()
        print("Starting local callback server...")
        
        # Start the callback server
        try:
            start_callback_server()
        except Exception as e:
            print(f"❌ Failed to start callback server: {e}")
            print()
            print("This might be because:")
            print(f"  - Port {OAUTH_CALLBACK_PORT} is already in use")
            print("  - Another application is using the port")
            print()
            print("Try closing other applications or change OAUTH_CALLBACK_PORT in the script.")
            return
    else:
        # Using Intuit's default redirect URI (no admin access needed)
        print("=" * 70)
        print("✅ NO REDIRECT URL CONFIGURATION NEEDED!")
        print("=" * 70)
        print()
        print("The script uses Intuit's default redirect URI automatically.")
        print("You do NOT need to:")
        print("  ❌ Add redirect URL to Intuit app")
        print("  ❌ Configure anything in developer portal")
        print("  ❌ Have admin access")
        print()
        print("Just follow these simple steps:")
        print()
    
    # Generate authorization URL
    auth_url = generate_auth_url()
    
    print()
    print("=" * 70)
    print("STEP 1: Authorize in Browser")
    print("=" * 70)
    print()
    print("✅ NO REDIRECT URL CONFIGURATION NEEDED!")
    print("   The script uses Intuit's default redirect URI automatically.")
    print("   You don't need to configure anything in Intuit Developer Portal.")
    print()
    print("Opening your browser...")
    print()
    
    # Open browser
    webbrowser.open(auth_url)
    
    print("In the browser:")
    print("1. Sign in with your Intuit account")
    print("   (Use account with 'Sandbox US Company 1' for sandbox)")
    print("2. Select your company")
    print("3. Click 'Connect' to authorize")
    print()
    print("After clicking 'Connect', you'll be redirected to a page.")
    print("That's normal! Just continue to Step 2 below.")
    print()
    if not USE_LOCAL_SERVER:
        print("If browser doesn't open, visit this URL manually:")
        print(auth_url)
        print()
    
    if USE_LOCAL_SERVER:
        print("After authorization, you'll be automatically redirected back.")
        print("The script will automatically capture the authorization code.")
        print()
        
        # Wait for callback
        success, error_msg = wait_for_callback(timeout=300)
        
        if not success:
            print(f"❌ Failed to receive callback: {error_msg}")
            return
        
        # Get the authorization code and realm ID
        auth_code = oauth_result["code"]
        realm_id = oauth_result["realm_id"]
        
        print("✅ Authorization code received!")
        print(f"   Realm ID: {realm_id}")
        print()
    else:
        # Manual mode - user needs to copy from URL
        print("=" * 70)
        print("STEP 2: Copy URL from Browser")
        print("=" * 70)
        print()
        print("📋 WHAT TO DO:")
        print("1. After clicking 'Connect', you'll be redirected to a page")
        print("2. Look at your browser's ADDRESS BAR (top of browser)")
        print("3. Copy the ENTIRE URL (select all and copy)")
        print("4. Paste it here in the terminal")
        print()
        print("The URL will look something like:")
        print("  https://developer.intuit.com/...?code=XXXXX&realmId=YYYYY")
        print()
        print("💡 Don't worry about what the page says - just copy the URL!")
        print("💡 The script will extract everything it needs automatically.")
        print()
        print("-" * 70)
        
        # Get full URL from user - extract code and realmId automatically
        full_url = input("Paste the ENTIRE redirect URL here: ").strip()
        if not full_url:
            print("❌ URL is required. Exiting.")
            return
        
        # Extract code and realmId from URL
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(full_url)
            params = urllib.parse.parse_qs(parsed.query)
            auth_code = params.get('code', [None])[0]
            realm_id = params.get('realmId', [None])[0]
            
            if not auth_code or not realm_id:
                print("❌ Could not extract code and realmId from URL")
                print("   Please check the URL format")
                return None
            
            print()
            print(f"✅ Extracted code: {auth_code[:20]}...")
            print(f"✅ Extracted realmId: {realm_id}")
            print()
        except Exception as e:
            print(f"❌ Error parsing URL: {e}")
            return None
    
    # Exchange code for tokens
    token_data = exchange_code_for_tokens(auth_code)
    
    if not token_data:
        print()
        print("=" * 70)
        print("❌ Token Exchange Failed")
        print("=" * 70)
        print()
        print("The authorization code couldn't be exchanged with your current credentials.")
        print()
        print("💡 SOLUTION: Use OAuth Playground to get tokens")
        print()
        print("1. Go to: https://developer.intuit.com/v2/OAuth2Playground")
        print("2. Enter your CLIENT_ID and CLIENT_SECRET from .env file")
        print("3. Use the authorization code you just got")
        print("4. Exchange for tokens in the playground")
        print("5. Run this simple setup:")
        print("   python3 setup_tokens.py")
        print("6. Paste the tokens when prompted")
        print()
        print("That's it! The script will save everything automatically.")
        print()
        return
    
    # Automatically save tokens to .env and cache
    print()
    print("=" * 70)
    print("✅ SUCCESS! Tokens obtained")
    print("=" * 70)
    print()
    
    # Update .env file automatically
    import re
    env_path = pathlib.Path(".env")
    if env_path.exists():
        env_content = env_path.read_text()
        
        # Update or add QBO_REFRESH_TOKEN
        if re.search(r'^QBO_REFRESH_TOKEN=', env_content, re.MULTILINE):
            env_content = re.sub(r'^QBO_REFRESH_TOKEN=.*$', f'QBO_REFRESH_TOKEN={token_data["refresh_token"]}', env_content, flags=re.MULTILINE)
        else:
            env_content += f'\nQBO_REFRESH_TOKEN={token_data["refresh_token"]}'
        
        # Update or add QBO_REALM_ID
        if re.search(r'^QBO_REALM_ID=', env_content, re.MULTILINE):
            env_content = re.sub(r'^QBO_REALM_ID=.*$', f'QBO_REALM_ID={realm_id}', env_content, flags=re.MULTILINE)
        else:
            env_content += f'\nQBO_REALM_ID={realm_id}'
        
        env_path.write_text(env_content)
        print("✅ Automatically updated .env file with tokens")
    else:
        print("⚠️  .env file not found. Please add manually:")
        print(f"QBO_REFRESH_TOKEN={token_data['refresh_token']}")
        print(f"QBO_REALM_ID={realm_id}")
    
    # Automatically save access token to cache
    import json
    from datetime import datetime, timedelta
    cache_file = pathlib.Path(".token_cache.json")
    cache_data = {
        "access_token": token_data["access_token"],
        "expires_at": (datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()
    }
    cache_file.write_text(json.dumps(cache_data))
    print("✅ Automatically saved access token to cache")
    print()
    
    print("Token details:")
    print(f"  Access Token: {token_data['access_token'][:30]}... (cached, expires in {token_data.get('expires_in', 3600)}s)")
    print(f"  Refresh Token: {token_data['refresh_token'][:30]}... (saved to .env)")
    print(f"  Realm ID: {realm_id} (saved to .env)")
    print()
    print("=" * 70)
    print()
    print("🎉 Setup Complete! You can now use the system:")
    print()
    print("  python3 quickbooks_client.py")
    print("  python3 create_estimate.py --json samples/quote_sample.json")
    print()
    print("⚠️  SECURITY REMINDER:")
    print("   - Never commit your .env file to version control")
    print("   - Keep your refresh token secure")
    print()

if __name__ == "__main__":
    main()
