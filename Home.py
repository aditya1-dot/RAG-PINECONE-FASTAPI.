import streamlit as st
from streamlit_lottie import st_lottie
import json
import base64
import streamlit.components.v1 as components

# Initialize session state
if 'email' not in st.session_state:
    st.session_state.email = None

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def main_bg(main_bg):
    main_bg_ext = 'png'
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] > .main {{
            background: url(data:image/{main_bg_ext};base64,{base64.b64encode(open(main_bg, "rb").read()).decode()});
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    
def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

def main():
    side_bg = 'background.png'
    main_bg(side_bg)
    st.header("***:red[QueryBridge]*** Your Own Rag Space", divider=True)

    col1, col2 = st.columns(spec=2)
    with col1:
        animation1 = load_lottiefile("Animation - 1737035977257.json")
        st_lottie(animation1, loop=True)
        st.divider()
        with st.container(height=430, border=False):
            st.title(":green[PineCone used for storing the vector embeddings]")
            st.markdown(">:orange[Namespace implemented to perform Multitenancy]")
            st.markdown(">:orange[E-mail id used to identify namespace.]")
            st.markdown(">:orange[No need to upload the same pdf again.]")
        st.divider()
        st.image("fastapi.png", use_container_width=True)
            
    with col2:
        with st.container(height=355, border=False):
            st.title(":green[Upload multiple pdfs at once Hasle Free!]")
            st.markdown('>:orange[Articles]')
            st.markdown('>:orange[Lab Manuals]')
            st.markdown('>:orange[Resume]')
        st.divider()
        with st.container(height=430, border=False):
            animation2 = load_lottiefile("database.json")
            st_lottie(animation2, loop=True)
        st.divider()
        with st.container(height=125, border=False):
            st.markdown('>:orange[Backend running on Flask]')
            st.markdown('>:orange[Two endpoints query and batchingest]')

    st.header(body=" ", divider=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('* :green[Lets Dive in to check the working of app]')

    with col2:
        if st.button(label="Login", use_container_width=True, icon="☑️"):
            st.switch_page("pages/Login.py")

    # Check for email in URL parameters
    query_params = st.query_params
    if 'email' in query_params and not st.session_state.email:
        st.session_state.email = query_params['email']
        st.switch_page("pages/Chat.py")

if __name__ == "__main__":
    main()