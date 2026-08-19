from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from models import ItemCreate, BuyItemRequest, DepositRequest, UpdateItemPrice
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["2. Quản lý Tài liệu & Ví tiền"])

@router.get("/my-wallet")
def get_my_wallet(user: dict = Depends(get_current_user)):
    return {"username": user["username"], "balance_eduxu": user["balance_eduxu"]}

@router.post("/deposit")
def deposit(req: DepositRequest, user: dict = Depends(get_current_user)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền nạp không hợp lệ")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance_eduxu = balance_eduxu + ? WHERE id = ?", (req.amount, user["id"]))
    conn.commit()
    conn.close()
    return {"message": f"Nạp thành công +{req.amount} EduXu!"}

@router.post("/items")
def create_item(item: ItemCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (title, price, content_url, seller_id) VALUES (?, ?, ?, ?)",
                   (item.title, item.price, item.content_url, user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Đăng bán tài liệu thành công!"}

@router.get("/items")
def list_items():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.id, items.title, items.price, users.username as seller 
        FROM items JOIN users ON items.seller_id = users.id ORDER BY items.id DESC
    """)
    items = cursor.fetchall()
    conn.close()
    return [dict(i) for i in items]

@router.put("/items/{item_id}/price")
def update_item_price(item_id: int, req: UpdateItemPrice, user: dict = Depends(get_current_user)):
    if req.price < 0:
        raise HTTPException(status_code=400, detail="Giá bán không hợp lệ!")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại!")
    if item["seller_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Bạn không có quyền đổi giá tài liệu này!")

    cursor.execute("UPDATE items SET price = ? WHERE id = ?", (req.price, item_id))
    conn.commit()
    conn.close()
    return {"message": "Cập nhật giá bán thành công!"}

@router.delete("/items/{item_id}")
def delete_item(item_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại!")
    if item["seller_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa tài liệu này!")

    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"message": "Đã xóa tài liệu thành công!"}

@router.post("/buy-item")
def buy_item(req: BuyItemRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (req.item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

    if user["balance_eduxu"] < item["price"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Số dư EduXu không đủ!")

    cursor.execute("UPDATE users SET balance_eduxu = balance_eduxu - ? WHERE id = ?", (item["price"], user["id"]))
    cursor.execute("UPDATE users SET balance_eduxu = balance_eduxu + ? WHERE id = ?", (item["price"], item["seller_id"]))
    conn.commit()
    conn.close()
    return {"message": "Mua tài liệu thành công!", "content_url": item["content_url"]}
