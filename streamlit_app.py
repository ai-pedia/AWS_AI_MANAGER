import streamlit as st
import json
import re
import time
import traceback # Added import for traceback
import os

SESSION_FILE = "session_state.json"

def load_session_state():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            try:
                state = json.load(f)
                st.session_state.messages = state.get("messages", [])
                st.session_state.conversation_flow = state.get("conversation_flow", {"active": False})
            except json.JSONDecodeError:
                st.session_state.messages = []
                st.session_state.conversation_flow = {"active": False}
    else:
        st.session_state.messages = []
        st.session_state.conversation_flow = {"active": False}

def save_session_state():
    state = {
        "messages": st.session_state.messages,
        "conversation_flow": st.session_state.conversation_flow,
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(state, f)


# Import EC2 service functions from the copied backend
from services.terraform_service import create_ec2, destroy_ec2, list_ec2
from utils.conversation_handler import execute_user_action # New import
from utils.ai_client import send_to_perplexity # New import

st.set_page_config(page_title="AWS AI Manager", layout="wide")

st.title("AWS AI Manager")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_flow" not in st.session_state:
    st.session_state.conversation_flow = {"active": False}

# Display welcome message if chat history is empty
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": """
Hello! I'm your AWS AI Manager. I can help you manage your AWS resources using natural language.

Here are some examples of what you can ask me:

*   `Create an EC2 instance`
*   `Destroy my S3 bucket named my-test-bucket`
*   `List all running EC2 instances`
*   `Estimate the cost of a t3.micro EC2 instance with 50GB storage`
*   `Modify EC2 instance i-0abcdef1234567890 root volume size to 100GB`

How can I help you with AWS today?
"""})

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("How can I help you with AWS today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process user input to determine intent or continue flow
    # This function will now handle the multi-turn logic and call EC2 functions
    # It will also decide if an AI response is needed
    ai_response_needed = execute_user_action(prompt)
    save_session_state()

    if ai_response_needed:
        with st.chat_message("assistant"):
            ai_response_content, error_message = send_to_perplexity(prompt)
            if ai_response_content:
                st.session_state.messages.append({"role": "assistant", "content": ai_response_content})
            else:
                st.session_state.messages.append({"role": "assistant", "content": f"AI communication failed: {error_message}"})
    st.rerun() # Rerun to update chat history