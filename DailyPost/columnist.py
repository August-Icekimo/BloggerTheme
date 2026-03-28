# DailyPost/columnist.py
import os
import glob
import frontmatter

class Columnist:
    def list_posts(self, posts_dir: str = 'posts/', status: str = 'all'):
        pattern = os.path.join(posts_dir, '**', '*.md')
        files   = glob.glob(pattern, recursive=True)
        if not files:
            print(f"No .md files found in {posts_dir}")
            return
        
        print(f"{'Title':<40} {'Post ID':<22} {'Status'}")
        print('-' * 75)
        
        for filepath in sorted(files):
            try:
                post      = frontmatter.load(filepath)
                title     = post.get('title', '(no title)')[:38]
                post_id   = str(post.get('post_id', '—'))
                published = post.get('published', False)
                pub_str   = 'published' if published else 'draft'
            except Exception:
                title, post_id, pub_str = '(no frontmatter)', '—', '—'
            
            if status == 'all' or status == pub_str:
                print(f"{title:<40} {post_id:<22} {pub_str}")
