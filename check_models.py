import google.generativeai as genai
import os

# Use the key from settings (hardcoded for this check as per user's previous edit)
api_key = "AIzaSyA9T6TtCVsHjdoGzfLPHghGWd0tunqbfl0"
genai.configure(api_key=api_key)

print(f"google-generativeai version: {genai.__version__}")

models_to_test = ['gemini-flash-latest', 'gemini-pro-latest']

for model_name in models_to_test:
    try:
        print(f"Testing {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"Success with {model_name}: {response.text}")
        break
    except Exception as e:
        print(f"Failed with {model_name}: {e}")
