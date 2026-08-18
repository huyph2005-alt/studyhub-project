from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models import PostCreate, CommentCreate
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["3. Diễn đàn thảo luận"])

@router.post("/posts")
def create_post(post: PostCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (title, content, author_id) VALUES (?, ?, ?)",
                   (post.title, post.content, user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Đăng bài thành công!"}

@router.get("/posts")
def get_posts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT posts.id, posts.title, posts.content, posts.created_at, users.username as author 
        FROM posts JOIN users ON posts.author_id = users.id ORDER BY posts.id DESC
    """)
    posts = cursor.fetchall()
    conn.close()
    return [dict(p) for p in posts]

@router.delete("/posts/{post_id}")
def delete_post(post_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT author_id FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại!")
    if post["author_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài viết này!")

    cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"message": "Đã xóa bài viết thành công!"}

@router.post("/comments")
def create_comment(comment: CommentCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
                   (comment.post_id, user["id"], comment.content))
    conn.commit()
    conn.close()
    return {"message": "Đã gửi bình luận!"}

@router.get("/posts/{post_id}/comments")
def get_comments(post_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT comments.content, users.username as commenter 
        FROM comments JOIN users ON comments.user_id = users.id 
        WHERE comments.post_id = ? ORDER BY comments.id ASC
    """, (post_id,))
    comments = cursor.fetchall()
    conn.close()
    return [dict(c) for c in comments]
