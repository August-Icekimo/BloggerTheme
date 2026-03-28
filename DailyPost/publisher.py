# DailyPost/publisher.py
import argparse
import sys
import os

# Add root folder so modules can be imported if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DailyPost.auth import get_credentials, get_blog_id
from DailyPost.data_journalist import DataJournalist
from DailyPost.reporter import Reporter
from DailyPost.columnist import Columnist
from googleapiclient.discovery import build

def cmd_push(args):
    dj = DataJournalist()
    fm, html = dj.markdown_to_html(args.file)
    
    try:
        service = build('blogger', 'v3', credentials=get_credentials())
        blog_id = get_blog_id()
    except Exception as e:
        print(f"Error authenticating with Blogger API: {e}")
        sys.exit(1)
        
    post_body = {
        "title":   fm.get('title', 'Untitled'),
        "content": html,
        "labels":  fm.get('labels', []),
    }
    
    post_id = fm.get('post_id')
    # Use boolean 'published' from frontmatter: True means LIVE, False means DRAFT
    is_draft = not fm.get('published', False)
    
    try:
        if post_id:
            print(f"Updating post {post_id}...")
            resp = service.posts().update(blogId=blog_id, postId=str(post_id), body=post_body).execute()
        else:
            print("Creating new post...")
            resp = service.posts().insert(blogId=blog_id, body=post_body, isDraft=is_draft).execute()
            
        print(f"Title : {resp.get('title')}")
        print(f"URL   : {resp.get('url', 'Draft — no URL yet')}")
        
        if not post_id:
            print(f"NEW POST ID: {resp.get('id')}")
            print(f"-> IMPORTANT: update your frontmatter in {args.file} with post_id: {resp.get('id')}")
    except Exception as e:
        print(f"Blogger API Error: {e}")
        sys.exit(1)

def cmd_pull(args):
    reporter = Reporter()
    reporter.pull(post_id=args.post_id, output_dir=args.output or 'posts/')

def cmd_list(args):
    columnist = Columnist()
    columnist.list_posts(status=args.status)

def main():
    parser = argparse.ArgumentParser(prog='DailyPost Publisher')
    sub = parser.add_subparsers(dest='command', required=True)

    p_push = sub.add_parser('push', help='Push local .md to Blogger')
    p_push.add_argument('file', help='Path to .md file')
    p_push.set_defaults(func=cmd_push)

    p_pull = sub.add_parser('pull', help='Pull post from Blogger to .md')
    p_pull.add_argument('--post-id', required=True, help='Blogger post ID')
    p_pull.add_argument('--output', help='Output directory (default: posts/)')
    p_pull.set_defaults(func=cmd_pull)

    p_list = sub.add_parser('list', help='List local drafts and their status')
    p_list.add_argument('--status', choices=['all', 'draft', 'published'], default='all')
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    
    # Check if the file for push command exists
    if args.command == 'push' and not os.path.isfile(args.file):
        print(f"Error: Markdown file '{args.file}' not found.")
        sys.exit(1)
        
    args.func(args)

if __name__ == '__main__':
    main()
