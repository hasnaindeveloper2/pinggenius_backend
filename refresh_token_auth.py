# refresh_token_generator.py

from google_auth_oauthlib.flow import InstalledAppFlow
import json

# Define the scopes you need
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
]

def generate_new_token():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Save the credentials to token.json
    with open('token.json', 'w') as token_file:
        token_file.write(creds.to_json())

    print("✅ New token.json file generated successfully!")

if __name__ == '__main__':
    generate_new_token()
