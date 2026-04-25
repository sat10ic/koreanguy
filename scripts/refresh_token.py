import os
import sys
import json
import requests
import hashlib
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _config

config = _config.load_config()

def generate_auth_code_url(app_id, redirect_uri):
    base_url = "https://api-t1.fyers.in/api/v3/generate-authcode"
    return f"{base_url}?client_id={app_id}&redirect_uri={redirect_uri}&response_type=code&state=sample_state"

def exchange_auth_code(app_id, secret_id, auth_code, redirect_uri):
    url = "https://api-t1.fyers.in/api/v3/validate-authcode"
    app_id_hash = hashlib.sha256(f"{app_id}:{secret_id}".encode()).hexdigest()
    
    payload = {
        "grant_type": "authorization_code",
        "appIdHash": app_id_hash,
        "code": auth_code
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        data = resp.json()
        if data.get('s') == 'ok':
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token')
            }
        else:
            print(f"Error: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def refresh_access_token(app_id, secret_id, refresh_token):
    url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
    app_id_hash = hashlib.sha256(f"{app_id}:{secret_id}".encode()).hexdigest()
    
    payload = {
        "grant_type": "refresh_token",
        "appIdHash": app_id_hash,
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        data = resp.json()
        if data.get('s') == 'ok':
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token')
            }
        return None
    except Exception as e:
        return None

def update_settings(tokens, settings_path):
    if not os.path.exists(settings_path): return
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
        settings['fyers_access_token'] = tokens['access_token']
        if 'refresh_token' in tokens:
            settings['fyers_refresh_token'] = tokens['refresh_token']
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
    except:
        pass

def extract_auth_code(value):
    raw = (value or "").strip()
    if not raw: return ""
    if "auth_code=" not in raw: return raw
    try:
        parsed = urlparse(raw)
        params = parse_qs(parsed.query)
        return (params.get("auth_code") or [""])[0].strip()
    except Exception:
        return raw

def main():
    app_id = os.environ.get("FYERS_CLIENT_ID", "")
    secret_id = os.environ.get("FYERS_SECRET_ID", "")
    
    if not app_id or not secret_id:
        swingedge_settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SwingEdge', 'config', 'settings.json')
        if os.path.exists(swingedge_settings_path):
            try:
                with open(swingedge_settings_path, 'r') as f:
                    settings = json.load(f)
                    app_id = app_id or settings.get('fyers_app_id', '')
                    secret_id = secret_id or settings.get('fyers_secret_id', '')
            except Exception as e:
                pass
                
    redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
    
    if not app_id or not secret_id:
        print("❌ FYERS_CLIENT_ID and FYERS_SECRET_ID environment variables must be set (or found in SwingEdge settings).")
        return 1
        
    auth_url = generate_auth_code_url(app_id, redirect_uri)
    print("=" * 60)
    print("STEP 1: Open this URL in your browser:")
    print()
    print(auth_url)
    print()
    print("STEP 2: Log in to Fyers and authorize the app")
    print("STEP 3: You'll be redirected to a URL with 'auth_code' in it")
    print("STEP 4: Copy the auth_code from the URL and paste below")
    print("=" * 60)
    print()
    
    auth_code = extract_auth_code(input("Enter auth_code or paste the full redirect URL: ").strip())
    if not auth_code:
        print("No auth code provided. Exiting.")
        return 1
        
    print("Exchanging auth code for tokens...")
    tokens = exchange_auth_code(app_id, secret_id, auth_code, redirect_uri)
    
    if tokens:
        print(f"✅ Success!")
        print(f"Set your environment variable (e.g. FYERS_TOKEN) to this:")
        print(tokens['access_token'])
        print()
        if os.path.exists(swingedge_settings_path):
            update_settings(tokens, swingedge_settings_path)
            print("Successfully saved tokens to SwingEdge/config/settings.json")
        return 0
    else:
        print("❌ Failed to exchange auth code.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
