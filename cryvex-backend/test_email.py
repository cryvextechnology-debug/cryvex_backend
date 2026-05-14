"""Quick test: send a real email via Brevo SMTP and print every server response."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from dotenv import load_dotenv
import os

load_dotenv()

SMTP_SERVER = os.getenv("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN")
SMTP_PASS = os.getenv("BREVO_SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
TO_EMAIL = input("Enter the test recipient email: ").strip()

print(f"\n--- SMTP Config ---")
print(f"Server:  {SMTP_SERVER}:{SMTP_PORT}")
print(f"Login:   {SMTP_LOGIN}")
print(f"Sender:  {SENDER_EMAIL}")
print(f"To:      {TO_EMAIL}")
print(f"-------------------\n")

msg = MIMEMultipart("alternative")
msg["Subject"] = "Cryvex Test Email"
msg["From"] = formataddr(("Cryvex AI", SENDER_EMAIL))
msg["To"] = TO_EMAIL
msg["Reply-To"] = SENDER_EMAIL

plain = "This is a test email from Cryvex AI. If you see this, email delivery is working."
html = """<html><body>
<h2 style="color:#4F46E5;">Cryvex Test Email</h2>
<p>This is a <strong>test email</strong> from Cryvex AI.</p>
<p>If you see this, email delivery is working correctly!</p>
</body></html>"""

msg.attach(MIMEText(plain, "plain"))
msg.attach(MIMEText(html, "html"))

try:
    print("[1] Connecting to SMTP server...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
    server.set_debuglevel(2)  # Full SMTP debug output
    
    print("\n[2] EHLO...")
    server.ehlo()
    
    print("\n[3] STARTTLS...")
    server.starttls()
    server.ehlo()
    
    print("\n[4] LOGIN...")
    server.login(SMTP_LOGIN, SMTP_PASS)
    
    print("\n[5] SENDMAIL...")
    result = server.sendmail(SENDER_EMAIL, TO_EMAIL, msg.as_string())
    print(f"\n[6] sendmail() result: {result}")
    print("    (Empty dict = accepted by server)")
    
    print("\n[7] QUIT...")
    server.quit()
    
    print("\n✅ Email sent successfully! Check inbox AND spam folder.")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
