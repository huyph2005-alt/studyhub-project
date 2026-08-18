from pydantic import BaseModel

class UserAuth(BaseModel):
    username: str
    password: str

class DepositRequest(BaseModel):
    amount: int

class ItemCreate(BaseModel):
    title: str
    price: int
    content_url: str

class BuyItemRequest(BaseModel):
    item_id: int

class PostCreate(BaseModel):
    title: str
    content: str

class CommentCreate(BaseModel):
    post_id: int
    content: str
