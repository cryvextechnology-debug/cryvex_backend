import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_brevo():
    api_key = os.getenv("BREVO_API_KEY") or os.getenv("BREVO_SMTP_PASSWORD")
    sender_email = os.getenv("BREVO_SENDER_EMAIL") or os.getenv("BREVO_SMTP_LOGIN")
    
    print(f"Testing Brevo API with Key: {api_key[:10]}...")
    print(f"Sender Email: {sender_email}")
    
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key
    }
    payload = {
        "sender": {"name": "Cryvex Test", "email": sender_email},
        "to": [{"email": "test@example.com"}], # Doesn't matter if it's fake for auth check
        "subject": "Test",
        "htmlContent": "<h1>Test</h1>"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
            
            if response.status_code == 401:
                print("\n[DIAGNOSIS] 401 Unauthorized: Your API key is invalid or not authorized.")
            elif response.status_code == 403:
                print("\n[DIAGNOSIS] 403 Forbidden: This usually means IP RESTRICTIONS are active in your Brevo settings.")
            elif response.status_code == 201:
                print("\n[DIAGNOSIS] Success! The API is working.")
            else:
                print(f"\n[DIAGNOSIS] Unexpected error: {response.status_code}")
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_brevo())
