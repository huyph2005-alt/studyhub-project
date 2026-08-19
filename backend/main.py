from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
from database import init_db, get_db
from routes import auth_routes, item_routes, post_routes

# Khởi tạo CSDL
init_db()

app = FastAPI(title="StudyHub API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route tạo Admin nhanh chóng
@app.get("/setup-admin")
@app.get("/api/setup-admin")
def setup_admin():
    conn = get_db()
    cursor = conn.cursor()
    hashed = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cursor.execute("DELETE FROM users WHERE username = 'admin'")
    cursor.execute("""
        INSERT INTO users (username, password, balance_eduxu, role) 
        VALUES ('admin', ?, 9999, 'admin')
    """, (hashed,))
    conn.commit()
    conn.close()
    return {"message": "Tao tai khoan Admin thanh cong: admin / admin123"}

# Gắn các router chức năng
app.include_router(auth_routes.router)
app.include_router(item_routes.router)
app.include_router(post_routes.router)

@app.get("/")
def home():
    return {"message": "StudyHub Backend is running properly!"}
