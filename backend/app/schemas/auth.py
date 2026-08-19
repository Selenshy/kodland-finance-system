from pydantic import BaseModel, EmailStr

from app.models.enums import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    account_id: int
    email: EmailStr
    full_name: str
    is_active: bool
    global_role: Role
    entity_ids: list[int] | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    global_role: Role = Role.VIEWER
    entity_role_ids: list[int] = []


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    global_role: Role | None = None
    password: str | None = None
