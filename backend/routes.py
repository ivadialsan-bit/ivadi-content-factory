from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Account, Post, Clip, Comment, Statistics, Pattern
from schemas import AccountCreate, PostCreate, ClipCreate, CommentCreate, PatternCreate
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["api"])

class AccountUpdate(BaseModel):
    is_active: bool

# ACCOUNTS
@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@router.post("/accounts")
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(
        Account.community_id == account.community_id,
        Account.token == account.token
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Аккаунт с таким ID и token уже существует")
    
    db_account = Account(
        name=account.name,
        platform=account.platform,
        community_id=account.community_id,
        token=account.token,
        is_active=account.is_active
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/accounts/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.id == account_id).first()

@router.patch("/accounts/{account_id}")
def update_account(account_id: int, update: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    account.is_active = update.is_active
    db.commit()
    db.refresh(account)
    return account

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    db.query(Account).filter(Account.id == account_id).delete()
    db.commit()
    return {"message": "Deleted"}

# POSTS
@router.get("/posts")
def get_posts(account_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Post)
    if account_id:
        query = query.filter(Post.account_id == account_id)
    return query.all()

@router.post("/posts")
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(
        account_id=post.account_id,
        theme=post.theme,
        caption=post.caption,
        image_path=post.image_path,
        status=post.status
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

@router.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    return db.query(Post).filter(Post.id == post_id).first()

# CLIPS
@router.get("/clips")
def get_clips(account_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Clip)
    if account_id:
        query = query.filter(Clip.account_id == account_id)
    return query.all()

@router.post("/clips")
def create_clip(clip: ClipCreate, db: Session = Depends(get_db)):
    db_clip = Clip(
        account_id=clip.account_id,
        title=clip.title,
        description=clip.description,
        video_path=clip.video_path,
        duration=clip.duration,
        status=clip.status
    )
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    return db_clip

@router.get("/clips/{clip_id}")
def get_clip(clip_id: int, db: Session = Depends(get_db)):
    return db.query(Clip).filter(Clip.id == clip_id).first()

# COMMENTS
@router.get("/comments")
def get_comments(post_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Comment)
    if post_id:
        query = query.filter(Comment.post_id == post_id)
    return query.all()

@router.post("/comments")
def create_comment(comment: CommentCreate, db: Session = Depends(get_db)):
    db_comment = Comment(
        post_id=comment.post_id,
        author=comment.author,
        text=comment.text
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/comments/{comment_id}")
def get_comment(comment_id: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.id == comment_id).first()

@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    db.query(Comment).filter(Comment.id == comment_id).delete()
    db.commit()
    return {"message": "Deleted"}

# PATTERNS
@router.get("/patterns")
def get_patterns(db: Session = Depends(get_db)):
    return db.query(Pattern).all()

@router.post("/patterns")
def create_pattern(pattern: PatternCreate, db: Session = Depends(get_db)):
    db_pattern = Pattern(
        theme=pattern.theme,
        heroes=pattern.heroes,
        conclusion=pattern.conclusion,
        hook=pattern.hook
    )
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)
    return db_pattern

# STATISTICS
@router.get("/stats/{post_id}")
def get_stats(post_id: int, db: Session = Depends(get_db)):
    return db.query(Statistics).filter(Statistics.post_id == post_id).all()

# SYNC VK DATA
from vk_sync import sync_account
import threading

@router.post("/accounts/{account_id}/sync")
def sync_account_data(account_id: int, db: Session = Depends(get_db)):
    """Синхронизирует данные аккаунта из VK"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    # Запускаем синхронизацию в отдельном потоке
    thread = threading.Thread(target=sync_account, args=(account_id,))
    thread.start()
    
    return {"message": "Синхронизация запущена", "account_id": account_id}
