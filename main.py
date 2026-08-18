from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import jwt
import bcrypt
from datetime import datetime, timedelta

app = FastAPI(title="StudyHub API", description="Hệ thống chia sẻ tài liệu, Diễn đàn & Ví EduXu")

# Cấu hình CORS để giao diện web kết nối được vào API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "khoa_bi_mat_studyhub_sieu_bao_mat"
ALGORITHM = "HS256"

# -------------------------------------------------------------
# 1. Khởi tạo CSDL đầy đủ các bảng
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'STUDENT'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        balance INTEGER DEFAULT 50,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        price INTEGER NOT NULL,
        content_url TEXT NOT NULL,
        FOREIGN KEY (seller_id) REFERENCES users (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users (id),
        FOREIGN KEY (item_id) REFERENCES items (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES users (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------
# 2. Schemas dữ liệu đầu vào
# -------------------------------------------------------------
class AuthRequest(BaseModel):
    username: str
    password: str

class DepositRequest(BaseModel):
    amount: int

class CreateItemRequest(BaseModel):
    title: str
    price: int
    content_url: str

class BuyItemRequest(BaseModel):
    item_id: int

class CreatePostRequest(BaseModel):
    title: str
    content: str

class CreateCommentRequest(BaseModel):
    post_id: int
    content: str

# -------------------------------------------------------------
# 3. Middleware xác thực Token (Phải đặt trước các API)
# -------------------------------------------------------------
def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn!")

# -------------------------------------------------------------
# 4. APIs Xác thực
# -------------------------------------------------------------
@app.post("/api/register", tags=["1. Xác thực"])
def register(data: AuthRequest):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    
    pwd_bytes = data.password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       (data.username, hashed, "STUDENT"))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", (user_id, 100))
        conn.commit()
        return {"status": "success", "message": f"Tạo tài khoản {data.username} thành công! Đã tặng 100 EduXu."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại!")
    finally:
        conn.close()

@app.post("/api/login", tags=["1. Xác thực"])
def login(data: AuthRequest):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=400, detail="Sai tài khoản hoặc mật khẩu!")
    
    pwd_bytes = data.password.encode('utf-8')[:72]
    stored_hash = user[2].encode('utf-8')
    
    if not bcrypt.checkpw(pwd_bytes, stored_hash):
        raise HTTPException(status_code=400, detail="Sai tài khoản hoặc mật khẩu!")
    
    payload = {
        "user_id": user[0],
        "username": user[1],
        "role": user[3],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": user[3]}

# -------------------------------------------------------------
# 5. APIs Diễn đàn Thảo luận (Posts & Comments)
# -------------------------------------------------------------
@app.post("/api/posts", tags=["2. Diễn đàn thảo luận"])
def create_post(data: CreatePostRequest, user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (author_id, title, content) VALUES (?, ?, ?)",
        (user["user_id"], data.title, data.content)
    )
    new_post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đăng bài thành công!", "post_id": new_post_id}

@app.get("/api/posts", tags=["2. Diễn đàn thảo luận"])
def get_all_posts():
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.id, p.title, p.content, p.created_at, u.username as author_name
    FROM posts p
    JOIN users u ON p.author_id = u.id
    ORDER BY p.created_at DESC
    """)
    posts = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "title": r[1], "content": r[2], "created_at": r[3], "author": r[4]}
        for r in posts
    ]

@app.post("/api/comments", tags=["2. Diễn đàn thảo luận"])
def create_comment(data: CreateCommentRequest, user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM posts WHERE id = ?", (data.post_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại!")
        
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (data.post_id, user["user_id"], data.content)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Bình luận thành công!"}

@app.get("/api/posts/{post_id}/comments", tags=["2. Diễn đàn thảo luận"])
def get_post_comments(post_id: int):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.id, c.content, c.created_at, u.username as commenter
    FROM comments c
    JOIN users u ON c.user_id = u.id
    WHERE c.post_id = ?
    ORDER BY c.created_at ASC
    """, (post_id,))
    comments = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "content": r[1], "created_at": r[2], "commenter": r[3]}
        for r in comments
    ]

# -------------------------------------------------------------
# 6. APIs Quản lý Tài liệu & Ví tiền
# -------------------------------------------------------------
@app.post("/api/items", tags=["3. Quản lý Tài liệu"])
def create_item(data: CreateItemRequest, user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (seller_id, title, price, content_url) VALUES (?, ?, ?, ?)",
        (user["user_id"], data.title, data.price, data.content_url)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đăng bán tài liệu thành công!"}

@app.get("/api/items", tags=["3. Quản lý Tài liệu"])
def list_items():
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT i.id, i.title, i.price, u.username as seller_name 
    FROM items i JOIN users u ON i.seller_id = u.id
    """)
    items = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "price": r[2], "seller": r[3]} for r in items]

@app.post("/api/deposit", tags=["4. Giao dịch & Ví tiền"])
def deposit_money(data: DepositRequest, user: dict = Depends(get_current_user)):
    """Nạp EduXu vào ví cá nhân"""
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền nạp phải lớn hơn 0!")
    
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (data.amount, user["user_id"]))
    cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (user["user_id"],))
    new_balance = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Nạp thành công {data.amount} EduXu!", "new_balance": new_balance}

@app.post("/api/buy-item", tags=["4. Giao dịch & Ví tiền"])
def buy_item(data: BuyItemRequest, user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    try:
        buyer_id = user["user_id"]
        cursor.execute("SELECT id, seller_id, price, content_url FROM items WHERE id = ?", (data.item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu!")
        
        item_id, seller_id, price, content_url = item
        if buyer_id == seller_id:
            raise HTTPException(status_code=400, detail="Bạn không thể tự mua tài liệu của chính mình!")
            
        cursor.execute("SELECT id FROM purchases WHERE buyer_id = ? AND item_id = ?", (buyer_id, item_id))
        if cursor.fetchone():
            return {"status": "success", "message": "Bạn đã mua tài liệu này rồi!", "content_url": content_url}
        
        cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (buyer_id,))
        buyer_wallet = cursor.fetchone()
        if not buyer_wallet or buyer_wallet[0] < price:
            raise HTTPException(status_code=400, detail="Số dư EduXu không đủ!")
        
        cursor.execute("UPDATE wallets SET balance = balance - ? WHERE user_id = ?", (price, buyer_id))
        cursor.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (price, seller_id))
        cursor.execute("INSERT INTO purchases (buyer_id, item_id) VALUES (?, ?)", (buyer_id, item_id))
        conn.commit()
        return {"status": "success", "message": "Thanh toán thành công!", "content_url": content_url}
    except Exception as e:
        conn.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/my-wallet", tags=["4. Giao dịch & Ví tiền"])
def get_my_wallet(user: dict = Depends(get_current_user)):
    conn = sqlite3.connect("studyhub.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM wallets WHERE user_id = ?", (user["user_id"],))
    wallet = cursor.fetchone()
    conn.close()
    return {"username": user["username"], "balance_eduxu": wallet[0] if wallet else 0}