import asyncio
from app.utils import email_service

async def test_email_formatting():
    business = "Test Corp"
    strategy = "MARKET ANALYSIS\nFocus on local growth.\n\nEXECUTION STEPS\n1. Launch ads.\n2. Scale operations."
    
    html = email_service.build_strategy_email(business, strategy)
    print("--- STRATEGY HTML ---")
    print(html[:1000])
    
    # We can't easily test sending without live credentials, 
    # but we can test the internal methods if they were accessible.
    # Since they are private/sync, we'll just check if it crashes in mock mode.
    
    # Temporarily force is_configured to False for mock testing
    email_service.is_configured = False
    await email_service.send_prediction_email("test@example.com", "Test Subject", html)
    print("\n[OK] Mock email dispatch successful.")

if __name__ == "__main__":
    asyncio.run(test_email_formatting())
