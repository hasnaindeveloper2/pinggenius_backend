import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

def send_email_smtp(to_email: str, subject: str, body: str):
    try:
        # Create message container
        message = MIMEMultipart()
        message['From'] = f'PingGenius <{SMTP_EMAIL}>'
        message['To'] = to_email
        message['Subject'] = subject

        # Add HTML body
        message.attach(MIMEText(body, 'html'))

        # Create SMTP session
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            
            # Send email
            server.send_message(message)
            
        print(f"✅ Email sent to {to_email}")
    except Exception as error:
        print(f"❌ SMTP Error: {str(error)}")

# If you need to use this in other files, you can import the function directly
# No need for module.exports as in Node.js
