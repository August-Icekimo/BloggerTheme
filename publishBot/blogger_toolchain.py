import os
import re
import yaml
import markdown
import argparse
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
# Define paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, '.env')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.pickle')

# Load environment variables
load_dotenv(ENV_PATH)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
BLOG_ID = os.getenv("BLOG_ID")
SCOPES = ['https://www.googleapis.com/auth/blogger']
TRANSPARENT_BASE64 = "data:image/png;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def parse_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract YAML frontmatter
    frontmatter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            content = parts[2]

    # PRE-PROCESS: Mermaid blocks -> <div class="mermaid">...</div>
    # Using regex to find ```mermaid \n ... \n ```
    mermaid_pattern = re.compile(r'```mermaid\n(.*?)\n```', re.DOTALL)
    content = mermaid_pattern.sub(r'<div class="mermaid">\n\1\n</div>', content)

    # PRE-PROCESS: YouTube {{youtube: ID}}
    yt_pattern = re.compile(r'\{\{youtube:\s*([a-zA-Z0-9_-]{11})\}\}')
    def yt_repl(m):
        vid = m.group(1)
        return f'<div class="youtubelazy" data-embed="{vid}"><figure><img alt="YouTube Video" class="lazy" data-src="https://i.ytimg.com/vi/{vid}/sddefault.jpg" src="{TRANSPARENT_BASE64}"></figure></div>'
    content = yt_pattern.sub(yt_repl, content)

    # Convert to HTML
    html = markdown.markdown(content, extensions=['fenced_code', 'tables'])

    # POST-PROCESS: Images to Lazy Loading
    # Regular markdown images: <img alt="..." src="..." />
    img_pattern = re.compile(r'<img\s+alt="([^"]*)"\s+src="([^"]+)"\s*/?>')
    html = img_pattern.sub(rf'<img alt="\1" class="lazy" data-src="\2" src="{TRANSPARENT_BASE64}" />', html)

    return frontmatter, html

def push_to_blogger(frontmatter, html):
    service = build('blogger', 'v3', credentials=get_credentials())
    
    post_body = {
        "title": frontmatter.get('title', 'Untitled Request'),
        "content": html,
        "labels": frontmatter.get('labels', [])
    }
    
    post_id = frontmatter.get('post_id')
    is_draft = not frontmatter.get('published', False)

    if post_id:
        print(f"Updating existing post {post_id}...")
        request = service.posts().update(blogId=BLOG_ID, postId=str(post_id), body=post_body)
    else:
        print("Creating a new post...")
        request = service.posts().insert(blogId=BLOG_ID, body=post_body, isDraft=is_draft)

    response = request.execute()
    
    print("\n=== Success ===")
    print(f"Post Title: {response.get('title')}")
    print(f"Post URL: {response.get('url', 'Draft -> No URL yet')}")
    if not post_id:
        print(f"NEW POST ID: {response.get('id')}")
        print("=> Remember to add 'post_id: %s' to your Markdown frontmatter!" % response.get('id'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Blogger Tech Blog Toolchain")
    parser.add_argument('markdown_file', help="Path to the markdown file")
    args = parser.parse_args()

    if not os.path.exists(args.markdown_file):
        print(f"File not found: {args.markdown_file}")
        exit(1)

    print("Parsing Markdown...")
    fm, html_content = parse_markdown(args.markdown_file)
    
    print("Pushing to Blogger...")
    try:
        push_to_blogger(fm, html_content)
    except Exception as e:
        print(f"Error communicating with Blogger API: {e}")
