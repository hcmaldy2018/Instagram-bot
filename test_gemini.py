import google.generativeai as genai

def test_gemini():
    try:
        print("Configuring Gemini API...")
        genai.configure(api_key="AIzaSyC-rDK4kRtXgZoTraV1M4HU7CjGf_BQs-c")
        
        print("\nTesting with gemini-1.5-pro-latest...")
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        print("Testing API with a simple prompt...")
        response = model.generate_content('Generate a short Instagram comment for a nature photo')
        
        print("\nAPI Response:")
        print(response.text)
        
    except Exception as e:
        print(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    test_gemini() 