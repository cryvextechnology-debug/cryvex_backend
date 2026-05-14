from config import settings

print("--- Testing Config Load ---")
print(f"Algorithm: {settings.ALGORITHM}")
print(f"Private Key Loaded: {settings.JWT_PRIVATE_KEY.startswith('-----BEGIN')}")
print(f"Public Key Loaded: {settings.JWT_PUBLIC_KEY.startswith('-----BEGIN')}")

if "\\n" in settings.JWT_PRIVATE_KEY:
    print("⚠️ WARNING: Your keys still contain literal '\\n' strings. Ensure your loader is handling them as newlines.")