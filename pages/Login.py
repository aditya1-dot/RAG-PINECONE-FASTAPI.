import streamlit as st
import requests
import webbrowser
from pathlib import Path
from utils.session_manager import SessionManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session_manager = SessionManager()

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

def main():
    initialize_session_state()
    
    # Debug: Print current working directory and sessions directory
    logger.info(f"Current working directory: {Path.cwd()}")
    logger.info(f"Sessions directory path: {session_manager.sessions_dir}")
    logger.info(f"Sessions directory exists: {session_manager.sessions_dir.exists()}")
    
    # Check if already logged in
    if st.session_state.get('authenticated') and st.session_state.get('email'):
        st.switch_page("pages/chat.py")
        return
    
    st.title("Login to QueryBridge")
    
    st.markdown("""
        <style>
            .stButton button {
                width: 100%;
                padding: 1rem;
                font-size: 1.2rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🔐 Sign in with Google"):
            webbrowser.open("http://localhost:5000/login", new=0)
    
    # Check for email and session in URL parameters
    query_params = st.query_params
    if 'email' in query_params and 'session' in query_params:
        email = query_params['email'][0]
        session_id = query_params['session'][0]
        
        logger.info(f"Received login callback with email: {email} and session_id: {session_id}")
        
        try:
            # Verify the session with Flask server
            response = requests.get(
                f"http://localhost:5000/verify-session/{email}",
                params={'session': session_id}
            )
            
            logger.info(f"Verification response status: {response.status_code}")
            logger.info(f"Verification response content: {response.json()}")
            
            if response.status_code == 200 and response.json().get('valid'):
                # Prepare session data
                session_data = {
                    'email': email,
                    'session_id': session_id,
                    'authenticated': True,
                    'user_id': response.json().get('user_id'),
                    'messages': []
                }
                
                # Save session using SessionManager
                try:
                    logger.info("Attempting to save session data...")
                    success = session_manager.save_session(session_id, session_data)
                    
                    if success:
                        logger.info(f"Session file should be at: {session_manager.sessions_dir / f'{session_id}.json'}")
                        logger.info(f"Session file exists: {(session_manager.sessions_dir / f'{session_id}.json').exists()}")
                        
                        # Store in session state
                        for key, value in session_data.items():
                            st.session_state[key] = value
                        
                        # Debug: Print session state
                        logger.info(f"Session state after login: {dict(st.session_state)}")
                        
                        # Redirect to chat with session ID
                        st.experimental_set_query_params()
                        webbrowser.open(f"http://localhost:8501/chat?session_id={session_id}")
                        st.rerun()
                    else:
                        st.error("Failed to save session data")
                except Exception as e:
                    logger.error(f"Error saving session: {str(e)}")
                    st.error(f"Error saving session: {str(e)}")
            else:
                st.error("Invalid session. Please log in again.")
        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            st.error(f"Error verifying session: {str(e)}")
    # else:
    #     st.error("Missing email or session ID in the URL parameters.")

if __name__ == "__main__":
    main()
