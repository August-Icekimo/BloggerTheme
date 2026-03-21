import os
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Define paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, '.env')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.pickle')

# Load environment variables
load_dotenv(ENV_PATH)
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
BLOG_ID = os.getenv("BLOG_ID")

SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing access token...")
            creds.refresh(Request())
        else:
            print("Starting new OAuth flow...")
            client_config = {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
            print("Token saved to token.pickle!")
            
    return creds

def main():
    if not CLIENT_ID or not CLIENT_SECRET or not BLOG_ID:
        print("Error: Missing CLIENT_ID, CLIENT_SECRET, or BLOG_ID in .env file.")
        return

    print("Authenticating with Blogger API...")
    try:
        creds = get_credentials()
    except Exception as e:
        print(f"Authentication failed: {e}")
        return
    
    # Build Blogger service
    service = build('blogger', 'v3', credentials=creds)
    
    print(f"\nFetching info for Blog ID: {BLOG_ID}...")
    try:
        blog = service.blogs().get(blogId=BLOG_ID).execute()
        print("\n=== Success! ===")
        print(f"Blog Name: {blog.get('name')}")
        print(f"URL: {blog.get('url')}")
        print(f"Total Posts: {blog.get('posts', {}).get('totalItems', 0)}")
        print("================\n")
        print("Blogger API is successfully connected and working!")
    except Exception as e:
        print(f"Error fetching blog details: {e}")

if __name__ == '__main__':
    main()
