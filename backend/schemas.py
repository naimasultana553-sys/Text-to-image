from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class ImageBase(BaseModel):
    prompt: str
    style: Optional[str] = None

class ImageCreate(ImageBase):
    pass

class Image(ImageBase):
    id: int
    user_id: int
    url: str
    created_at: datetime

    class Config:
        orm_mode = True
