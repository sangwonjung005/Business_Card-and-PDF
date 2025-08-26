import streamlit as st
import requests

st.title("🧪 Simple Test App")
st.write("This is a simple test app without OpenCV")

# Simple GPT-OSS test
def test_gpt_oss():
    try:
        API_URL = "https://api-inference.huggingface.co/models/openai/gpt-oss-20b"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": "Hello, how are you?",
            "parameters": {"max_new_tokens": 100, "temperature": 0.7}
        }
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.status_code == 200
    except:
        return False

if st.button("Test GPT-OSS"):
    if test_gpt_oss():
        st.success("✅ GPT-OSS API working!")
    else:
        st.error("❌ GPT-OSS API failed")

st.write("If you see this, the app is working without OpenCV!")
