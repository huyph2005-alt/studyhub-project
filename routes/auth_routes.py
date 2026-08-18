from fastapi import APIRouter, HTTPException
from database import get_db
from models import UserAuth
from auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api", tags=["1. Xác thực"])

@router.post("/register")
def register(user_data: UserAuth):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (user_data.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại!")
    
    hashed = hash_password(user_data.password)
    cursor.execute("INSERT INTO users (username, password, balance_eduxu) VALUES (?, ?, 100)", (user_data.username, hashed))
    conn.commit()
    conn.close()
    return {"message": "Đăng ký thành công! Nhận ngay 100 EduXu."}

@router.post("/login")
def login(user_data: UserAuth):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (user_data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Sai tên đăng nhập hoặc mật khẩu!")

    token = create_access_token({"user_id": user["id"], "username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}
