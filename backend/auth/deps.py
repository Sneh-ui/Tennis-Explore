import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.auth.utils import decode_access_token
from backend.structured_data.database import get_db_connection

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


def get_current_user_db(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates JWT and fetches fresh user row from DB.
    Useful for /auth/me and future protected routes.
    """
    payload = get_current_user(credentials)
    user_id = payload.get("sub")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, role, profile_pic, created_at
                FROM auth.users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="User not found")
            return dict(row)
    finally:
        conn.close()


def require_admin(current_user: dict = Depends(get_current_user_db)):
    """
    Ensures current user has Admin role.
    """
    role = (current_user.get("role") or "").strip().lower()
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
