import smtplib
from email.mime.text import MIMEText
import os

# Replace this with your Gmail sending logic if needed
async def send_email(to: str, subject: str, body: str):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = os.getenv("FROM_EMAIL")  # e.g. no-reply@pinggenius.com
    msg["To"] = to

    # Your actual SMTP logic here (or reuse Gmail API)
    print(f"Mock send to: {to} ✅")
