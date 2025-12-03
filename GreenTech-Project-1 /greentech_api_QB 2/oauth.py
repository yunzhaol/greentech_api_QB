# Python/oauth.py
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Environment variables - set these in your .env file
CLIENT_ID = os.getenv("QBO_CLIENT_ID")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("QBO_REFRESH_TOKEN")
QBO_MODE = os.getenv("QBO_MODE", "sandbox")  # 'sandbox' or 'production'

# Token cache
_token_cache = {
    "access_token": None,
    "expires_at": None
}

def _load_token_cache():
    """Load token cache from file if it exists"""
    import json
    import pathlib
    cache_file = pathlib.Path(".token_cache.json")
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if data.get("access_token") and data.get("expires_at"):
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now() < expires_at:
                    _token_cache["access_token"] = data["access_token"]
                    _token_cache["expires_at"] = expires_at
                    return True
        except Exception:
            pass
    return False

def _save_token_cache():
    """Save token cache to file"""
    import json
    import pathlib
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        cache_file = pathlib.Path(".token_cache.json")
        data = {
            "access_token": _token_cache["access_token"],
            "expires_at": _token_cache["expires_at"].isoformat()
        }
        cache_file.write_text(json.dumps(data))

# Load cache on import
_load_token_cache()

def get_token_endpoint():
    """Returns the OAuth token endpoint URL"""
    return "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

def refresh_access_token(refresh_token: str) -> dict:
    """
    Exchanges a refresh token for a new access token.
    
    Args:
        refresh_token: Valid QuickBooks refresh token
        
    Returns:
        dict with 'access_token', 'refresh_token', 'expires_in', etc.
        
    Raises:
        Exception if token refresh fails
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in environment")
    
    token_url = get_token_endpoint()
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    
    print(f"[OAuth] Refreshing access token...")
    
    response = requests.post(
        token_url,
        headers=headers,
        data=data,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    
    if response.status_code == 200:
        token_data = response.json()
        print(f"[OAuth] ✅ Token refreshed successfully")
        print(f"[OAuth] Access token expires in {token_data.get('expires_in')} seconds")
        
        # Handle both camelCase and snake_case response formats
        # Intuit API sometimes returns camelCase (refreshToken, accessToken)
        # Normalize to snake_case for consistency
        if 'refreshToken' in token_data and 'refresh_token' not in token_data:
            token_data['refresh_token'] = token_data.pop('refreshToken')
        if 'accessToken' in token_data and 'access_token' not in token_data:
            token_data['access_token'] = token_data.pop('accessToken')
        
        # Update environment variable with new refresh token if provided
        new_refresh = token_data.get('refresh_token')
        if new_refresh and new_refresh != refresh_token:
            print(f"[OAuth] ⚠️  New refresh token received - update your .env file!")
            print(f"[OAuth] New refresh token: {new_refresh[:20]}...")
        
        return token_data
    else:
        error_msg = f"Token refresh failed: {response.status_code} - {response.text}"
        print(f"[OAuth] ❌ {error_msg}")
        # Don't raise immediately - let caller handle fallback
        raise Exception(error_msg)

def get_access_token(force_refresh: bool = False) -> str:
    """
    Returns a valid access token, refreshing if necessary.
    Implements caching to avoid unnecessary token refreshes.
    
    Args:
        force_refresh: If True, forces a token refresh even if cached token is valid
        
    Returns:
        Valid access token string
        
    Raises:
        Exception if unable to get valid token
    """
    global _token_cache
    
    # Load cache from file first
    _load_token_cache()
    
    # Check if we have a cached token that's still valid (with 5-minute buffer)
    if not force_refresh and _token_cache["access_token"] and _token_cache["expires_at"]:
        time_until_expiry = (_token_cache["expires_at"] - datetime.now()).total_seconds()
        if time_until_expiry > 300:  # More than 5 minutes left
            print(f"[OAuth] Using cached access token (expires in {int(time_until_expiry)}s)")
            return _token_cache["access_token"]
    
    # Need to refresh the token
    if not REFRESH_TOKEN:
        # If we have a cached token but it's expired, try to use it anyway as last resort
        if _token_cache["access_token"]:
            print("[OAuth] ⚠️  No refresh token available, using cached token (may be expired)")
            return _token_cache["access_token"]
        raise ValueError("QBO_REFRESH_TOKEN not set in environment. Run initial OAuth flow first.")
    
    try:
        token_data = refresh_access_token(REFRESH_TOKEN)
    except Exception as e:
        # If refresh fails but we have a cached token, use it as fallback
        if _token_cache["access_token"]:
            print(f"[OAuth] ⚠️  Token refresh failed: {str(e)[:100]}")
            print("[OAuth] Using cached access token as fallback (may be expired)")
            return _token_cache["access_token"]
        # If no cached token, raise the error
        raise
    
    # Cache the new token
    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = datetime.now() + timedelta(seconds=token_data["expires_in"])
    _save_token_cache()  # Persist to file
    
    return _token_cache["access_token"]

def get_auth_header() -> dict:
    """
    Returns authorization header dict for QuickBooks API requests.
    
    Returns:
        dict: {'Authorization': 'Bearer <token>'}
    """
    token = get_access_token()
    return {"Authorization": f"Bearer {token}"}

def revoke_token(token: str) -> bool:
    """
    Revokes an access or refresh token.
    Used when disconnecting from QuickBooks.
    
    Args:
        token: Access token or refresh token to revoke
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set")
    
    revoke_url = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    
    payload = {
        "token": token
    }
    
    response = requests.post(
        revoke_url,
        headers=headers,
        json=payload,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    
    if response.status_code == 200:
        print("[OAuth] ✅ Token revoked successfully")
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None
        return True
    else:
        print(f"[OAuth] ❌ Token revocation failed: {response.status_code}")
        return False

# Test function
if __name__ == "__main__":
    print("Testing OAuth token management...")
    try:
        token = get_access_token()
        print(f"✅ Access token obtained: {token[:20]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
