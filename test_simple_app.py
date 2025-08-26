import streamlit as st
import requests
import json

st.title("🧪 Simple Test App")
st.write("This is a simple test app without OpenCV")

# Simple GPT-OSS test with detailed error handling
def test_gpt_oss():
    try:
        API_URL = "https://api-inference.huggingface.co/models/openai/gpt-oss-20b"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": "Hello, how are you?",
            "parameters": {"max_new_tokens": 100, "temperature": 0.7}
        }
        
        st.write("🔄 Calling GPT-OSS API...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        st.write(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            st.write(f"📄 Response: {result}")
            return True, "Success"
        else:
            st.write(f"❌ Error Response: {response.text}")
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        st.write(f"💥 Exception: {str(e)}")
        return False, str(e)

if st.button("Test GPT-OSS"):
    success, message = test_gpt_oss()
    if success:
        st.success("✅ GPT-OSS API working!")
    else:
        st.error(f"❌ GPT-OSS API failed: {message}")

st.write("If you see this, the app is working without OpenCV!")

# Fallback test with OpenAI
st.markdown("---")
st.subheader("🔄 OpenAI Fallback Test")

def test_openai():
    try:
        import os
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return False, "No OpenAI API key found"
            
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=50
        )
        return True, response.choices[0].message.content
        
    except Exception as e:
        return False, str(e)

if st.button("Test OpenAI"):
    success, message = test_openai()
    if success:
        st.success(f"✅ OpenAI working: {message}")
    else:
        st.error(f"❌ OpenAI failed: {message}")
