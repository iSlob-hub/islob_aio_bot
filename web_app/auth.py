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

SECRET = os.environ.get("WEB_APP_SESSION_SECRET", "your_session_secret")
API_TOKEN = os.environ.get("BOT_TOKEN")

serializer = URLSafeSerializer(SECRET)
security = HTTPBearer(auto_error=False)


def verify_telegram_auth(data: dict) -> bool:
    try:
        auth_data = data.copy()
        hash_ = auth_data.pop("hash")
        
        # Видаляємо порожні поля, як робить Telegram
        filtered_data = {k: v for k, v in auth_data.items() if v and str(v).strip()}
        
        # Створюємо рядок для перевірки
        check_string = "\n".join([f"{k}={filtered_data[k]}" for k in sorted(filtered_data)])
        print(f"DEBUG: Check string: {check_string}")
        
        # Створюємо секретний ключ
        secret_key = hashlib.sha256(API_TOKEN.encode()).digest()
        
        # Обчислюємо hash
        h = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        
        print(f"DEBUG: Expected hash: {h}")
        print(f"DEBUG: Received hash: {hash_}")
        
        result = h == hash_
        print(f"DEBUG: Hash verification result: {result}")
        
        return result
        
    except Exception as e:
        print(f"DEBUG: Error in verify_telegram_auth: {e}")
        return False


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
