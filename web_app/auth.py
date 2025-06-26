import hashlib
import hmac
from itsdangerous import URLSafeSerializer
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.models import User
from dotenv import load_dotenv
import os
from fastapi.responses import RedirectResponse

load_dotenv()

SECRET = "your_session_secret"
API_TOKEN = os.environ.get("BOT_TOKEN")

serializer = URLSafeSerializer(SECRET)
security = HTTPBearer(auto_error=False)


def verify_telegram_auth(data: dict) -> bool:
    auth_data = data.copy()
    hash_ = auth_data.pop("hash")
    check_string = "\n".join([f"{k}={auth_data[k]}" for k in sorted(auth_data)])
    secret_key = hashlib.sha256(API_TOKEN.encode()).digest()
    h = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return h == hash_


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials if credentials else request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401)

    try:
        data = serializer.loads(token)
        telegram_id = data.get("telegram_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await User.find_one(User.telegram_id == str(telegram_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user
