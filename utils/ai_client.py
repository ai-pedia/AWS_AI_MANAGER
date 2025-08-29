import os
from dotenv import load_dotenv
import openai
import streamlit as st # For st.error

# Load environment variables (for PERPLEXITY_API_KEY)
load_dotenv()

# Configure Perplexity AI client
# Ensure PERPLEXITY_API_KEY is set in your .env file
client = openai.OpenAI(api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")

def send_to_perplexity(prompt):
    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": """You are a helpful AI assistant that specializes in AWS cloud resource management. Your responses must be strictly limited to AWS-related topics. If a user asks a question unrelated to AWS, you must politely decline to answer and state that you can only assist with AWS cloud resources.
                You can help create, destroy, list, and estimate costs for various AWS resources.
                When a user asks to perform an AWS action (like create, destroy, list, or estimate cost), please acknowledge the request briefly and *do not* ask for specific parameters. The application will handle parameter collection. For other general AWS-related questions, respond conversationally.
                """},
                {"role": "user", "content": prompt}
            ],
            # Removed response_format parameter
        )
        return response.choices[0].message.content, None # Return content and no error
    except Exception as e:
        error_msg = f"Error communicating with Perplexity AI: {e}"
        st.error(error_msg) # Still display in UI
        return None, error_msg # Return None content and error message