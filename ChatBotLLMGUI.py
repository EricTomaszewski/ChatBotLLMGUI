import streamlit as st
import requests
import time
import json
import uuid
import os

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

# --- HELPER: API KEY MASKING ---
def mask_api_key(key):
    if not key:
        return ""
    if len(key) <= 4:
        return key
    return "*" * (len(key) - 4) + key[-4:]

# --- HELPER: CHAT PERSISTENCE ---
CHAT_HISTORY_FILE = "chat_history.json"

def load_chats():
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_chats(chats):
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(chats, f, indent=4)

# --- SESSION STATE (MEMORY) ---
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()

if not st.session_state.chats:
    # Create a default new chat if none exist
    new_chat_id = str(uuid.uuid4())
    st.session_state.chats[new_chat_id] = {
        "title": "New Chat",
        "messages": []
    }
    st.session_state.current_chat_id = new_chat_id
elif "current_chat_id" not in st.session_state:
    # Default to the most recently created/updated chat (simplification: just first key)
    # Ideally, we'd sort by timestamp, but keys are unordered. Let's pick the last key or random.
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]

# --- SIDEBAR: CHAT HISTORY & SETTINGS ---
with st.sidebar:
    st.header("Settings")

    # Initialize session state for API key
    if "real_api_key" not in st.session_state:
        st.session_state.real_api_key = DEFAULT_API_KEY

    # Initialize input field value
    if "api_key_input" not in st.session_state:
        st.session_state.api_key_input = mask_api_key(st.session_state.real_api_key)

    def update_api_key():
        new_val = st.session_state.api_key_input
        st.session_state.real_api_key = new_val
        st.session_state.api_key_input = mask_api_key(new_val)

    st.text_input("API Key", key="api_key_input", on_change=update_api_key, help="Enter your API Key. It will be masked.")
    api_key = st.session_state.real_api_key

    slug = st.text_input("Workspace Slug", value=DEFAULT_WORKSPACE_SLUG)
    mode = st.radio("Mode", ["chat", "query"], index=0, help="'Query' uses only your documents. 'Chat' uses general knowledge + docs.")

    @st.dialog("Delete Chat?")
    def delete_chat_dialog(chat_id_to_delete):
        st.write("Are you sure you want to delete this chat?")
        col1, col2 = st.columns(2)
        if col1.button("Cancel", use_container_width=True):
            st.rerun()
        if col2.button("Delete", use_container_width=True, type="primary"):
            del st.session_state.chats[chat_id_to_delete]

            # If deleted current chat, switch to another
            if chat_id_to_delete == st.session_state.current_chat_id:
                if st.session_state.chats:
                    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
                else:
                    new_id = str(uuid.uuid4())
                    st.session_state.chats[new_id] = {"title": "New Chat", "messages": []}
                    st.session_state.current_chat_id = new_id

            save_chats(st.session_state.chats)
            st.rerun()

    @st.dialog("Clear All Chats?")
    def clear_all_chats_dialog():
        st.write("Are you sure you want to delete ALL chats? This cannot be undone.")
        col1, col2 = st.columns(2)
        if col1.button("Cancel", use_container_width=True):
            st.rerun()
        if col2.button("Delete All", use_container_width=True, type="primary"):
            st.session_state.chats = {}
            new_chat_id = str(uuid.uuid4())
            st.session_state.chats[new_chat_id] = {"title": "New Chat", "messages": []}
            st.session_state.current_chat_id = new_chat_id
            save_chats(st.session_state.chats)
            st.rerun()

    if st.button("🗑️ Clear All Chats"):
        clear_all_chats_dialog()

    st.markdown("---")
    st.title("💬 Chat History")

    # Check if current chat is empty to disable "New Chat"
    current_chat_obj = st.session_state.chats.get(st.session_state.current_chat_id)
    is_current_empty = len(current_chat_obj["messages"]) == 0 if current_chat_obj else True

    if st.button("➕ New Chat", use_container_width=True, disabled=is_current_empty):
        new_chat_id = str(uuid.uuid4())
        st.session_state.chats[new_chat_id] = {
            "title": "New Chat",
            "messages": []
        }
        st.session_state.current_chat_id = new_chat_id
        save_chats(st.session_state.chats)
        st.rerun()

    # Display existing chats
    # We'll display them in reverse order of creation (assuming dict preserves insertion order in modern Python)
    # or we could add a timestamp field. For now, just listing keys.
    chat_ids = list(st.session_state.chats.keys())

    for chat_id in reversed(chat_ids):
        chat = st.session_state.chats[chat_id]
        title = chat.get("title", "New Chat")

        # Using columns to create a "Button" look or just simple buttons
        col1, col2 = st.columns([0.85, 0.15])

        # Select Chat Button
        if col1.button(title, key=f"chat_btn_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()

        # Delete Chat Button
        if col2.button("🗑️", key=f"del_btn_{chat_id}", help="Delete this chat"):
            delete_chat_dialog(chat_id)

# --- MAIN PAGE ---
st.title("🤖 Local AI Chat")
st.caption("Powered by AnythingLLM")

# Get current chat
current_chat = st.session_state.chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

# --- DISPLAY CHAT HISTORY ---
for message in messages:
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
    # 0. Update title if it's the first message
    if len(messages) == 0:
        # Simple title generation: First 30 chars of prompt
        new_title = prompt[:30] + ("..." if len(prompt) > 30 else "")
        current_chat["title"] = new_title
        save_chats(st.session_state.chats)
        # Rerun to update the sidebar title instantly?
        # Rerunning might interrupt the flow. Let's rely on next interaction or force update sidebar somehow?
        # Streamlit sidebar updates require a rerun usually.
        # We can accept that the title updates on the NEXT interaction, or force a rerun but that clears the input.
        # Let's just update the state and save.

    # 1. Display user message immediately
    st.chat_message("user").markdown(prompt)
    messages.append({"role": "user", "content": prompt})
    save_chats(st.session_state.chats)

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
    messages.append({"role": "assistant", "content": full_response})
    save_chats(st.session_state.chats)