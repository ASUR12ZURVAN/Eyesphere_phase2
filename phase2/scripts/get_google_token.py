import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    """
    Run this script locally to generate the GOOGLE_REFRESH_TOKEN.
    You need a 'credentials.json' file from Google Cloud Console.
    """
    if not os.path.exists('credentials.json'):
        print("Error: 'credentials.json' not found.")
        print("Please download it from Google Cloud Console (APIs & Services > Credentials).")
        return

    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    print("\nSuccessfully authenticated!")
    print("Add these to your .env file:")
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")

if __name__ == '__main__':
    main()
