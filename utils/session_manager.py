import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        # Get the absolute path to the project root (parent of current directory)
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.sessions_dir = self.project_root / "sessions"
        
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Sessions directory: {self.sessions_dir}")
        
        # Create sessions directory if it doesn't exist
        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Sessions directory created/exists at: {self.sessions_dir}")
        except Exception as e:
            logger.error(f"Error creating sessions directory: {str(e)}")
            raise
    
    def save_session(self, session_id, data):
        try:
            # Ensure session_id is safe to use as a filename
            safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
            session_file = self.sessions_dir / f"{safe_session_id}.json"
            logger.info(f"Saving session to: {session_file}")
            
            # Ensure the sessions directory exists
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file with pretty printing for debugging
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Session saved successfully. File exists: {session_file.exists()}")
            return True
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            raise
    def load_session(self, session_id):
        try:
            safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
            session_file = self.sessions_dir / f"{safe_session_id}.json"
            logger.info(f"Loading session from: {session_file}")
            
            if session_file.exists():
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Session loaded successfully: {data}")
                    return data
            else:
                logger.warning(f"Session file does not exist: {session_file}")
                return None
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            raise