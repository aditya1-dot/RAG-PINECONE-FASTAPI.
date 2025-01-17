import streamlit as st
import requests
import json
from streamlit_chat import message
from utils.session_manager import SessionManager

session_manager = SessionManager()

def check_authentication():
    query_params = st.query_params
    if 'session' in query_params:
        session_id = query_params['session']
        session_data = session_manager.load_session(session_id)
        
        if session_data:
            for key, value in session_data.items():
                st.session_state[key] = value
            return True
    
    if not st.session_state.get('authenticated'):
        st.query_params.clear()
        return False
    return True

def handle_logout():
    if st.session_state.get('session_id'):
        requests.get(
            "http://localhost:5000/logout",
            params={'session': st.session_state.session_id}
        )
        session_manager.save_session(st.session_state.session_id, {})
    
    st.session_state.clear()
    st.query_params.clear()

def upload_files(files, email):
    if not files:
        return None
    
    files_list = [('files', file) for file in files]
    data = {"email": email}
    
    try:
        response = requests.post(
            "http://localhost:8000/batch-ingest",
            files=files_list,
            data=data
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error uploading files: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to server: {str(e)}")
        return None

def query_documents(query_text, email):
    try:
        payload = {
            "query": query_text,
            "email": email
        }
        
        response = requests.post(
            "http://localhost:8000/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract only the 'answer' field from the response
            if isinstance(response_data, dict) and 'answer' in response_data:
                return {"response": response_data['answer']}
            else:
                return {"response": "Could not find answer in response"}
        else:
            st.error(f"Error querying documents: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to server: {str(e)}")
        return None
def initialize_chat_history():
    if 'messages' not in st.session_state:
        st.session_state.messages = []

def main():
    if not check_authentication():
        st.warning("Please log in to continue")
        return
    
    initialize_chat_history()
    
    st.title(f"Welcome {st.session_state.get('email', 'User')}!")
    
    # Sidebar content
    with st.sidebar:
        # Logout button
        if st.button("Logout", type="secondary"):
            handle_logout()
            st.rerun()
        
        st.divider()
        
        # File uploader in sidebar
        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload one or more PDF files to chat with"
        )
        
        if uploaded_files:
            if st.button("Process Documents"):
                with st.spinner("Uploading and processing documents..."):
                    result = upload_files(uploaded_files, st.session_state.email)
                    if result:
                        st.success("Documents processed successfully!")
                        for file in uploaded_files:
                            st.write(f"✓ {file.name}")
    
    # Main chat area
    st.subheader("Chat with your documents")
    
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Save session data
        session_data = {
            'email': st.session_state.email,
            'session_id': st.session_state.session_id,
            'authenticated': st.session_state.authenticated,
            'user_id': st.session_state.user_id,
            'messages': st.session_state.messages
        }
        session_manager.save_session(st.session_state.session_id, session_data)
        
        # Query the FastAPI backend
        with st.spinner("Searching documents..."):
            response_data = query_documents(prompt, st.session_state.email)
            
            # Handle the response
            if response_data is not None:
                if isinstance(response_data, dict):
                    response = response_data.get('response', str(response_data))
                else:
                    response = str(response_data)
            else:
                response = "Sorry, I couldn't process your question. Please try again."
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
        
        # Save updated messages
        session_data['messages'] = st.session_state.messages
        session_manager.save_session(st.session_state.session_id, session_data)

if __name__ == "__main__":
    main()