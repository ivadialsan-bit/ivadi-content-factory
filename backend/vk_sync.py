import requests
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Account, Post, Clip, Comment
import time

Base.metadata.create_all(bind=engine)

VK_API_URL = 'https://vk-api-proxy.ivadialsan.workers.dev/method'
VK_API_VERSION = '5.131'

def get_vk_posts(community_id: str, token: str, db: Session):
    """Загружает посты"""
    try:
        print(f"[VK] Загружаю посты для {community_id}...")
        
        group_id = community_id.replace('-', '')
        
        params = {
            'owner_id': f'-{group_id}',
            'count': 100,
            'v': VK_API_VERSION,
            'access_token': token
        }
        
        response = requests.get(f'{VK_API_URL}/wall.get', params=params, timeout=10)
        data = response.json()
        
        if 'error' in data:
            print(f"[ERROR] {data['error'].get('error_msg', 'Unknown')}")
            return False
        
        posts = data.get('items', [])
        print(f"[VK] Найдено {len(posts)} постов")
        
        account = db.query(Account).filter(Account.community_id == community_id).first()
        
        for post in posts:
            if post.get('is_pinned'):
                continue
            
            existing_post = db.query(Post).filter(
                Post.account_id == account.id,
                Post.vk_url == f"https://vk.com/wall-{group_id}_{post['id']}"
            ).first()
            
            if not existing_post:
                text = post.get('text', '')[:100]
                theme = text[:50] if text else "Пост"
                
                new_post = Post(
                    account_id=account.id,
                    theme=theme,
                    caption=post.get('text', ''),
                    status='published',
                    views=post.get('views', {}).get('count', 0),
                    likes=post.get('likes', {}).get('count', 0),
                    comments_count=post.get('comments', {}).get('count', 0),
                    vk_url=f"https://vk.com/wall-{group_id}_{post['id']}",
                    published_at=datetime.fromtimestamp(post.get('date', 0))
                )
                db.add(new_post)
                print(f"  ✓ Пост #{post['id']}")
        
        db.commit()
        print("[VK] Посты ✓\n")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}\n")
        db.rollback()
        return False

def get_vk_clips(community_id: str, token: str, db: Session):
    """Загружает клипы из стены"""
    try:
        print(f"[VK] Загружаю клипы...")
        
        group_id = community_id.replace('-', '')
        account = db.query(Account).filter(Account.community_id == community_id).first()
        
        params = {
            'owner_id': f'-{group_id}',
            'count': 100,
            'v': VK_API_VERSION,
            'access_token': token
        }
        
        response = requests.get(f'{VK_API_URL}/wall.get', params=params, timeout=10)
        data = response.json()
        
        if 'error' in data:
            print(f"[WARNING] wall.get error\n")
            return False
        
        posts = data.get('items', [])
        video_count = 0
        
        for post in posts:
            attachments = post.get('attachments', [])
            for attachment in attachments:
                if attachment.get('type') == 'clip':
                    clip = attachment.get('clip', {})
                    clip_id = clip.get('id')
                    owner_id = clip.get('owner_id')
                    
                    if not clip_id or not owner_id:
                        continue
                    
                    video_path = f"https://vk.com/clip{owner_id}_{clip_id}"
                    
                    existing_clip = db.query(Clip).filter(
                        Clip.account_id == account.id,
                        Clip.video_path == video_path
                    ).first()
                    
                    if not existing_clip:
                        new_clip = Clip(
                            account_id=account.id,
                            title=clip.get('title', 'Клип'),
                            description=clip.get('description', ''),
                            video_path=video_path,
                            duration=clip.get('duration', 0),
                            status='published',
                            views=clip.get('views', 0),
                            likes=clip.get('likes', {}).get('count', 0) if isinstance(clip.get('likes'), dict) else 0,
                            comments_count=0,
                            published_at=datetime.fromtimestamp(post.get('date', 0))
                        )
                        db.add(new_clip)
                        video_count += 1
                        print(f"  ✓ {clip.get('title', 'Клип')}")
        
        db.commit()
        print(f"[VK] Клипов: {video_count} ✓\n")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}\n")
        db.rollback()
        return False

def get_vk_comments(community_id: str, token: str, db: Session):
    """Загружает комментарии"""
    try:
        print(f"[VK] Загружаю комментарии...")
        
        group_id = community_id.replace('-', '')
        account = db.query(Account).filter(Account.community_id == community_id).first()
        
        posts = db.query(Post).filter(Post.account_id == account.id).all()
        total_comments = 0
        
        for post in posts[:5]:
            try:
                vk_post_id = post.vk_url.split('_')[-1]
                
                params = {
                    'owner_id': f'-{group_id}',
                    'post_id': vk_post_id,
                    'count': 20,
                    'v': VK_API_VERSION,
                    'access_token': token,
                    'extended': 1
                }
                
                response = requests.get(f'{VK_API_URL}/wall.getComments', params=params, timeout=10)
                data = response.json()
                
                if 'error' in data:
                    continue
                
                comments = data.get('items', [])
                profiles = {p['id']: p for p in data.get('profiles', [])}
                
                for comment in comments:
                    existing_comment = db.query(Comment).filter(
                        Comment.post_id == post.id,
                        Comment.text == comment.get('text', '')
                    ).first()
                    
                    if not existing_comment:
                        author = comment.get('from_id')
                        if author in profiles:
                            author_name = f"{profiles[author].get('first_name', '')} {profiles[author].get('last_name', '')}".strip()
                        else:
                            author_name = f"User#{author}"
                        
                        new_comment = Comment(
                            post_id=post.id,
                            author=author_name,
                            text=comment.get('text', ''),
                            likes=comment.get('likes', {}).get('count', 0) if isinstance(comment.get('likes'), dict) else 0
                        )
                        db.add(new_comment)
                        total_comments += 1
                
                time.sleep(0.3)
                
            except Exception as e:
                continue
        
        db.commit()
        print(f"[VK] Комментариев: {total_comments} ✓\n")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}\n")
        db.rollback()
        return False

def sync_account(account_id: int):
    """Синхронизирует данные"""
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            print(f"[ERROR] Account not found")
            return False
        
        print(f"\n{'='*60}")
        print(f"SYNC: {account.name}")
        print(f"ID: {account.community_id}")
        print(f"{'='*60}\n")
        
        success = True
        success &= get_vk_posts(account.community_id, account.token, db)
        time.sleep(1)
        success &= get_vk_clips(account.community_id, account.token, db)
        time.sleep(1)
        success &= get_vk_comments(account.community_id, account.token, db)
        
        print(f"{'='*60}")
        print("✓ ГОТОВО" if success else "✗ ОШИБКИ")
        print(f"{'='*60}\n")
        
        return success
        
    finally:
        db.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        sync_account(int(sys.argv[1]))
