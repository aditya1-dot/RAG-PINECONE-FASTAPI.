import os
import pathlib
import json
import secrets
from datetime import timedelta
from collections import defaultdict
import time
import logging

import requests
from flask import Flask, session, abort, redirect, request, jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
from flask_cors import CORS
from utils.session_manager import SessionManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask("Google Login App")
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("app_secret_key", secrets.token_hex(16))

# Initialize SessionManager
session_manager = SessionManager()

# Session storage
valid_sessions = {}

def cleanup_old_sessions():
    current_time = time.time()
    for session_id in list(valid_sessions.keys()):
        if current_time - valid_sessions[session_id]['timestamp'] > 3600:  # 1 hour timeout
            del valid_sessions[session_id]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")
with open(client_secrets_file, "r") as f:
    client_secrets = json.load(f)

GOOGLE_CLIENT_ID = client_secrets["web"]["client_id"]

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ],
    redirect_uri="http://localhost:5000/callback"
)

@app.route("/")
def index():
    return """
    <html>
    <head>
        <title>QueryBridge Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }
            .container {
                text-align: center;
                padding: 2rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .google-btn {
                background: #4285f4;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            .google-btn:hover {
                background: #357abd;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to QueryBridge</h1>
            <a href="/login" class="google-btn">Sign in with Google</a>
        </div>
    </body>
    </html>
    """

@app.route("/login")
def login():
    cleanup_old_sessions()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        
        email = id_info.get("email")
        user_id = id_info.get("sub")
        
        # Store session information in memory
        session_id = secrets.token_urlsafe(32)
        valid_sessions[session_id] = {
            'email': email,
            'user_id': user_id,
            'timestamp': time.time()
        }
        
        # Prepare and save session data using SessionManager
        session_data = {
            'email': email,
            'session_id': session_id,
            'authenticated': True,
            'user_id': user_id,
            'messages': []
        }
        
        try:
            logger.info(f"Saving session data for user: {email}")
            session_manager.save_session(session_id, session_data)
            logger.info("Session data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save session data: {str(e)}")
            # Continue with redirect even if session save fails
        
        # Redirect to Streamlit with session information
        redirect_url = f"http://localhost:8501/chat?email={email}&session={session_id}"
        return redirect(redirect_url)
    
    except Exception as e:
        print(f"Error in authentication: {str(e)}")
        return f"Authentication failed: {str(e)}", 400

@app.route("/verify-session/<email>")
def verify_session(email):
    session_id = request.args.get('session')
    if session_id and session_id in valid_sessions:
        if valid_sessions[session_id]['email'] == email:
            return jsonify({
                'valid': True,
                'user_id': valid_sessions[session_id]['user_id']
            })
    return jsonify({'valid': False}), 401

@app.route("/logout")
def logout():
    session_id = request.args.get('session')
    if session_id in valid_sessions:
        del valid_sessions[session_id]
    return redirect("http://localhost:8501")

if __name__ == "__main__":
    app.run(port=5000, debug=True)