import streamlit as st
import requests
import json

st.title("🧪 Simple Test App")
st.write("This is a simple test app without OpenCV")

# Test different GPT-OSS models
def test_gpt_oss_models():
    models = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b", 
        "microsoft/DialoGPT-medium",
        "gpt2"
    ]
    
    results = {}
    
    for model in models:
        try:
            API_URL = f"https://api-inference.huggingface.co/models/{model}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "inputs": "Hello, how are you?",
                "parameters": {"max_new_tokens": 50, "temperature": 0.7}
            }
            
            st.write(f"🔄 Testing {model}...")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                results[model] = {"status": "Success", "response": result}
                st.success(f"✅ {model} working!")
            else:
                results[model] = {"status": f"HTTP {response.status_code}", "error": response.text}
                st.error(f"❌ {model} failed: HTTP {response.status_code}")
                
        except Exception as e:
            results[model] = {"status": "Exception", "error": str(e)}
            st.error(f"💥 {model} exception: {str(e)}")
    
    return results

if st.button("Test All GPT-OSS Models"):
    results = test_gpt_oss_models()
    
    st.markdown("---")
    st.subheader("📊 Test Results")
    for model, result in results.items():
        with st.expander(f"{model} - {result['status']}"):
            st.json(result)

# Simple OpenAI test
st.markdown("---")
st.subheader("🔄 OpenAI Test")

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

# Manual API key test
st.markdown("---")
st.subheader("🔑 Manual API Key Test")

manual_key = st.text_input("Enter OpenAI API Key (for testing):", type="password")
if manual_key and st.button("Test Manual Key"):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=manual_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=50
        )
        st.success(f"✅ Manual key working: {response.choices[0].message.content}")
    except Exception as e:
        st.error(f"❌ Manual key failed: {str(e)}")

st.write("If you see this, the app is working without OpenCV!") 
