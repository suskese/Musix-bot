# core/spotify_oauth.py
import os
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

if __name__ == "__main__":
    print("[Spotify OAuth] Starting test server on http://localhost:8888 ... (Ctrl+C to stop)")
    class StandaloneHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/test":
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Spotify OAuth server is running.")
            elif parsed.path == "/callback":
                qs = parse_qs(parsed.query)
                code = qs.get("code", [None])[0]
                state = qs.get("state", [None])[0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                msg = f"<h1>Spotify callback received!</h1><p>Code: {code}</p><p>State: {state}</p>"
                self.wfile.write(msg.encode())
            else:
                self.send_response(404)
                self.end_headers()
    server = HTTPServer(('0.0.0.0', 8888), StandaloneHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Spotify OAuth] Server stopped.")
        server.server_close()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID") or "YOUR_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET") or "YOUR_CLIENT_SECRET"
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI") or "YOUR_URL:PORT/callback"
SCOPE = "user-read-currently-playing user-read-playback-state"
TOKEN_FILE = os.path.join("cache", "spotify_tokens.json")

class SpotifyOAuthHandler:
    def __init__(self):
        self.tokens = self._load_tokens()

    def _load_tokens(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_tokens(self):
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tokens, f)

    def get_auth_url(self, user_id):
        params = {
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "scope": SCOPE,
            "state": str(user_id)
        }
        url = "https://accounts.spotify.com/authorize?" + "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
        return url

    def start_local_http_server(self, user_id):
        import logging
        code_holder = {}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                print(f"[SpotifyOAuth] Received request: {parsed.path}")
                if parsed.path == "/callback":
                    qs = parse_qs(parsed.query)
                    code = qs.get("code", [None])[0]
                    state = qs.get("state", [None])[0]
                    if state == str(user_id):
                        code_holder["code"] = code
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b"<h1>Spotify authorization complete. You can close this window.</h1>")
                        print("[SpotifyOAuth] Callback received and code stored.")
                    else:
                        self.send_response(400)
                        self.end_headers()
                        print("[SpotifyOAuth] Callback received with wrong state.")
                elif parsed.path == "/test":
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"Spotify OAuth server is running.")
                    print("[SpotifyOAuth] /test endpoint hit.")
                else:
                    self.send_response(404)
                    self.end_headers()
        print("[SpotifyOAuth] Starting temporary OAuth server on http://localhost:8888 ...")
        server = HTTPServer(('0.0.0.0', 8888), Handler)
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        thread.join(timeout=120)
        server.server_close()
        print("[SpotifyOAuth] Temporary OAuth server stopped.")
        return code_holder.get("code")

    def exchange_code(self, code):
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET
        }
        resp = requests.post("https://accounts.spotify.com/api/token", data=data)
        if resp.status_code == 200:
            return resp.json()
        return None

    def refresh_token(self, refresh_token):
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET
        }
        resp = requests.post("https://accounts.spotify.com/api/token", data=data)
        if resp.status_code == 200:
            return resp.json()
        return None

    def get_access_token(self, user_id):
        user_id = str(user_id)
        if user_id in self.tokens:
            token_info = self.tokens[user_id]
            if token_info.get("expires_at", 0) > int(__import__('time').time()):
                return token_info["access_token"]
            # Refresh
            refreshed = self.refresh_token(token_info["refresh_token"])
            if refreshed and "access_token" in refreshed:
                token_info["access_token"] = refreshed["access_token"]
                token_info["expires_at"] = int(__import__('time').time()) + refreshed.get("expires_in", 3600)
                self.tokens[user_id] = token_info
                self._save_tokens()
                return token_info["access_token"]
        return None

    def authorize_user(self, user_id, send_link_callback=None, timeout=120):
        url = self.get_auth_url(user_id)
        if send_link_callback:
            send_link_callback(url)
        # Start local server and wait for callback
        code = self.start_local_http_server(user_id)
        if not code:
            return False
        token_info = self.exchange_code(code)
        if token_info and "access_token" in token_info:
            token_info["expires_at"] = int(__import__('time').time()) + token_info.get("expires_in", 86400)
            self.tokens[str(user_id)] = token_info
            self._save_tokens()
            return True
        return False

    def get_currently_playing(self, user_id):
        access_token = self.get_access_token(user_id)
        if not access_token:
            return None
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        return None

spotify_oauth = SpotifyOAuthHandler()
