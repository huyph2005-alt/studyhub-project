import sqlite3
import bcrypt

DATABASE_NAME = "studyhub.db"

def get_db():
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance_eduxu INTEGER DEFAULT 100,
            role TEXT DEFAULT 'member'
        )
    """)

    # Tự động bổ sung các cột nếu database cũ bị thiếu
    for col_def in ["balance_eduxu INTEGER DEFAULT 100", "role TEXT DEFAULT 'member'"]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
        except Exception:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            content_url TEXT NOT NULL,
            seller_id INTEGER NOT NULL,
            FOREIGN KEY (seller_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL,
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

    # Kiểm tra và tạo tài khoản Admin an toàn
    try:
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed_admin_pw = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute("INSERT INTO users (username, password, balance_eduxu, role) VALUES ('admin', ?, 9999, 'admin')", (hashed_admin_pw,))
    except Exception:
        pass

    conn.commit()
    conn.close()
