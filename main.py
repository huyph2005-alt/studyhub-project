from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes import auth_routes, item_routes, post_routes

# Khởi tạo CSDL khi chạy
init_db()

app = FastAPI(title="StudyHub API", version="2.0")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các router chức năng
app.include_router(auth_routes.router)
app.include_router(item_routes.router)
app.include_router(post_routes.router)

@app.get("/")
def home():
    return {"message": "StudyHub Backend is running properly!"}
