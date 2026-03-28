# DailyPost/reporter.py
import re
import os
from datetime import datetime
from googleapiclient.discovery import build
from auth import get_credentials, get_blog_id
from data_journalist import DataJournalist

class Reporter:
    def __init__(self):
        self.dj      = DataJournalist()
        self.service = build('blogger', 'v3', credentials=get_credentials())
        self.blog_id = get_blog_id()

    def pull(self, post_id: str, output_dir: str = 'posts/'):
        print(f"Fetching post {post_id}...")
        try:
            post = self.service.posts().get(
                blogId=self.blog_id, postId=post_id
            ).execute()
        except Exception as e:
            print(f"Error: {e}")
            raise SystemExit(1)

        title      = post.get('title', 'Untitled')
        html       = post.get('content', '')
        labels     = [l['name'] for l in post.get('labels', [])]
        published  = post.get('status') == 'LIVE'
        pub_at     = post.get('published', '')

        # HTML -> Markdown via DataJournalist
        markdown_body = self.dj.html_to_markdown(html)

        slug     = self._slugify(title)
        
        # Build frontmatter
        fm_lines = [
            "---",
            f"title: {title}"
        ]
        
        if labels:
            fm_lines.append("labels:")
            for l in labels:
                fm_lines.append(f"  - {l}")
        else:
            fm_lines.append("labels: []")
            
        fm_lines.append(f"published: {'true' if published else 'false'}")
        fm_lines.append(f"post_id: {post_id}")
        fm_lines.append(f"published_at: {pub_at}")
        fm_lines.append("---")
        fm_lines.append("")
        fm_lines.append(markdown_body)
        
        frontmatter = "\n".join(fm_lines)

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{slug}.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter)

        print(f"Saved: {out_path}")

    def _slugify(self, title: str) -> str:
        s = title.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'[\s_-]+', '-', s)
        return s[:60] if s else 'untitled-post'
