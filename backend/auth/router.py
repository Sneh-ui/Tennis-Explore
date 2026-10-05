from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr

from backend.structured_data.database import get_db_connection
from backend.auth.utils import verify_password, create_access_token, hash_password
from backend.auth.deps import get_current_user_db, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    profile_pic: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    password = payload.password

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, password_hash, role, profile_pic
                FROM auth.users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            user = dict(row)

            if not verify_password(password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            token = create_access_token(
                {"sub": str(user["id"]), "email": user["email"], "role": user["role"], "name": user["name"]}
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                    "profile_pic": user["profile_pic"],
                },
            }
    finally:
        conn.close()


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user_db)):
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user["role"],
        "profile_pic": current_user["profile_pic"],
    }


# ------------------- Admin User CRUD -------------------

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "Analyst"
    profile_pic: Optional[str] = None


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    profile_pic: Optional[str] = None


@router.get("/users", response_model=List[UserResponse])
def list_users(admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, role, profile_pic, created_at
                FROM auth.users
                ORDER BY id ASC
                """
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "email": r["email"],
                    "role": r["role"],
                    "profile_pic": r["profile_pic"],
                }
                for r in rows
            ]
    finally:
        conn.close()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest, admin: dict = Depends(require_admin)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # check duplicate email
            cur.execute("SELECT id FROM auth.users WHERE LOWER(email)=LOWER(%s)", (payload.email.strip(),))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already exists")

            hashed = hash_password(payload.password)
            cur.execute(
                """
                INSERT INTO auth.users (name, email, password_hash, role, profile_pic)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, email, role, profile_pic
                """,
                (
                    payload.name.strip(),
                    payload.email.strip().lower(),
                    hashed,
                    payload.role.strip() or "Analyst",
                    payload.profile_pic,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, role, profile_pic FROM auth.users WHERE id=%s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(row)
    finally:
        conn.close()


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UpdateUserRequest, admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email FROM auth.users WHERE id=%s", (user_id,))
            existing = cur.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="User not found")

            fields = []
            values = []

            if payload.name is not None:
                if not payload.name.strip():
                    raise HTTPException(status_code=400, detail="Name cannot be empty")
                fields.append("name=%s")
                values.append(payload.name.strip())

            if payload.email is not None:
                email = payload.email.strip().lower()
                # check duplicate
                cur.execute(
                    "SELECT id FROM auth.users WHERE LOWER(email)=LOWER(%s) AND id<>%s",
                    (email, user_id),
                )
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Email already exists")
                fields.append("email=%s")
                values.append(email)

            if payload.password is not None:
                if len(payload.password) < 6:
                    raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
                fields.append("password_hash=%s")
                values.append(hash_password(payload.password))

            if payload.role is not None:
                fields.append("role=%s")
                values.append(payload.role.strip())

            if payload.profile_pic is not None:
                fields.append("profile_pic=%s")
                values.append(payload.profile_pic)

            if not fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            values.append(user_id)
            cur.execute(
                f"UPDATE auth.users SET {', '.join(fields)}, updated_at=NOW() WHERE id=%s RETURNING id, name, email, role, profile_pic",
                tuple(values),
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    # prevent self-delete
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth.users WHERE id=%s RETURNING id", (user_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            conn.commit()
            return None
    finally:
        conn.close()
