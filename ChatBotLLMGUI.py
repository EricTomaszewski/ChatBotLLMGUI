import streamlit as st
import requests
import time

# --- CONFIGURATION (Or use the Sidebar in the UI) ---
# You can hardcode these if you don't want to paste them every time
# Old: DEFAULT_API_KEY = "42F04BR-..."
# New:
if "default_api_key" in st.secrets:
    DEFAULT_API_KEY = st.secrets["default_api_key"]
else:
    DEFAULT_API_KEY = "" # Handle case where secret is missing 
DEFAULT_WORKSPACE_SLUG = "eric-first" 
BASE_URL = "http://localhost:3001"

# --- PAGE SETUP ---
st.set_page_config(page_title="AnythingLLM Chat", page_icon="🤖")
st.title("🤖 Local AI Chat")
st.caption("Powered by AnythingLLM")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("API Key", value=DEFAULT_API_KEY, type="password")
    slug = st.text_input("Workspace Slug", value=DEFAULT_WORKSPACE_SLUG)
    mode = st.radio("Mode", ["chat", "query"], index=0, help="'Query' uses only your documents. 'Chat' uses general knowledge + docs.")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- SESSION STATE (MEMORY) ---
# This keeps the chat history alive while the app is running
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- DISPLAY CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- HELPER: STREAMING EFFECT ---
def stream_text(text):
    """Simulates typing effect like Gemini/ChatGPT"""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02) # Adjust speed here

# --- MAIN CHAT LOGIC ---
if prompt := st.chat_input("Message AnythingLLM..."):
    # 1. Display user message immediately
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prepare API Request
    endpoint = f"{BASE_URL}/api/v1/workspace/{slug}/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "message": prompt,
        "mode": mode
    }

    # 3. Fetch Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Show a spinner while waiting for the server
            with st.spinner("Thinking..."):
                response = requests.post(endpoint, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                ai_text = data.get('textResponse', 'No response text found.')
                
                # Stream the result to the UI (Visual effect only)
                # Note: AnythingLLM API returns full text at once, we simulate streaming for UX
                response_stream = stream_text(ai_text)
                for chunk in response_stream:
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                response_placeholder.error(error_msg)
                full_response = error_msg

        except Exception as e:
            error_msg = f"Connection Failed: {e}"
            response_placeholder.error(error_msg)
            full_response = error_msg

    # 4. Save Assistant Response to History
    st.session_state.messages.append({"role": "assistant", "content": full_response})