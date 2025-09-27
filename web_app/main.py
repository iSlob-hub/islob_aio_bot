from fastapi import FastAPI, Request, Query, Depends, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from datetime import datetime
from functools import wraps
from app.db.database import init_db
from app.db.models import User, TrainingSession, MorningQuiz
from typing import Optional
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from web_app.auth import verify_telegram_auth, get_current_user, serializer
from web_app.statistics_router import router as statistics_router
from web_app.notifications_router import router as notifications_router
from web_app.bot_settings_router import router as bot_settings_router
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
from fastapi.staticfiles import StaticFiles

load_dotenv()


BOT_TOKEN = os.environ.get("BOT_TOKEN")
TG_BOT_USERNAME = os.environ.get("TG_BOT_USERNAME")

ADMIN_IDS = [
    "591812219",
    "379872548",
    "5916038251"
]

app = FastAPI()

# Підключаємо роутери
app.include_router(statistics_router)
app.include_router(notifications_router)
app.include_router(bot_settings_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Ensure the uploads directory exists and mount it using an absolute path
FILES_DIR = Path(BASE_DIR).parent / "internal_files"
FILES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(FILES_DIR)), name="files")

@app.on_event("startup")
async def startup_event():
    await init_db()


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access protected endpoints"""
    if user.telegram_id not in ADMIN_IDS:
        raise HTTPException(
            status_code=403, 
            detail="Доступ заборонено! Ви маєте бути адміністратором."
        )
    return user


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {
            "request": request, 
            "bot": TG_BOT_USERNAME, 
            "current_user": None,
            "auth_url": f"{os.environ.get('BASE_HOST')}/auth/telegram"
        }
    )


@app.get("/auth/telegram")
async def auth_telegram(
    request: Request,
    id: int,
    first_name: str = "",
    last_name: str = "",
    username: str = "",
    photo_url: str = "",
    auth_date: str = "",
    hash: str = ""
):
    # Формуємо дані для перевірки, додаючи тільки непорожні поля
    user_data = {"id": id}
    
    if first_name:
        user_data["first_name"] = first_name
    if last_name:
        user_data["last_name"] = last_name
    if username:
        user_data["username"] = username
    if photo_url:
        user_data["photo_url"] = photo_url
    if auth_date:
        user_data["auth_date"] = auth_date
    
    # Додаємо hash для перевірки
    user_data["hash"] = hash
    
    print(f"DEBUG: Received auth data: {user_data}")
    
    # Перевіряємо валідність Telegram авторизації
    if not verify_telegram_auth(user_data):
        print("DEBUG: Telegram auth verification failed")
        return templates.TemplateResponse("access_denied.html", {
            "request": request,
            "bot_username": TG_BOT_USERNAME,
            "message": "Помилка авторизації Telegram."
        })
    
    print(f"DEBUG: Telegram auth verified successfully for user {id}")

    user = await User.find_one(User.telegram_id == str(id))
    if not user:
        print(f"DEBUG: User {id} not found in database")
        return templates.TemplateResponse("not_registered.html", {
            "request": request,
            "bot_username": TG_BOT_USERNAME
        })
    
    if user.telegram_id not in ADMIN_IDS:
        print(f"DEBUG: User {id} is not admin")
        return templates.TemplateResponse("access_denied.html", {
            "request": request,
            "bot_username": TG_BOT_USERNAME,
            "message": "Доступ заборонено."
        })

    print(f"DEBUG: Creating session for admin user {id}")
    token = serializer.dumps({"telegram_id": user.telegram_id})

    response = RedirectResponse("/customers")
    response.set_cookie("session", token, httponly=True)
    return response


@app.get("/customers", response_class=HTMLResponse)
async def show_customers(request: Request, user: User = Depends(get_admin_user)):
    users = await User.find_all().to_list()
    return templates.TemplateResponse("customers.html", {"request": request, "users": users, "current_user": user})


@app.get("/training-sessions", response_class=HTMLResponse)
async def training_sessions(
    request: Request,
    telegram_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: User = Depends(get_admin_user)
):
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        return templates.TemplateResponse(
            "training_sessions.html",
            {"request": request, "error": f"No user with Telegram ID: {telegram_id}", "sessions": [], "current_user": user},
        )

    query = TrainingSession.find(TrainingSession.user_id == str(telegram_id))

    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        query = query.find(TrainingSession.training_started_at >= dt_from)
    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d")
        query = query.find(TrainingSession.training_started_at <= dt_to)

    sessions_raw = await query.to_list()

    sessions = jsonable_encoder(sessions_raw)

    return templates.TemplateResponse(
        "training_sessions.html",
        {
            "request": request,
            "sessions": sessions,
            "user": user_profile,
            "date_from": date_from,
            "date_to": date_to,
            "current_user": user
        }
    )


@app.get("/profile", response_class=HTMLResponse)
async def user_profile(request: Request, telegram_id: str = Query(...), user: User = Depends(get_admin_user)):
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        return templates.TemplateResponse(
            "profile.html",
            {"request": request, "error": f"No user with Telegram ID: {telegram_id}", "current_user": user}
        )

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user_profile,
            "current_user": user
        }
    )


@app.post("/upload-training-file")
async def upload_training_file(
    request: Request,
    user_telegram_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_admin_user)
):
    recipient = await User.find_one(User.telegram_id == user_telegram_id)
    # Save uploads under the absolute internal files directory
    user_dir = FILES_DIR / user_telegram_id
    user_dir.mkdir(parents=True, exist_ok=True)

    file_path = user_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_url = f"/files/{user_telegram_id}/{file.filename}"

    recipient.training_file_url = file_url
    await recipient.save()

    return RedirectResponse(f"/profile?telegram_id={user_telegram_id}", status_code=302)


@app.post("/pause-payment")
async def pause_payment(
    request: Request,
    telegram_id: str,
    user: User = Depends(get_admin_user)
):
    """Поставити оплату користувача на паузу"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    user_profile.paused_payment = True
    await user_profile.save()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


@app.post("/resume-payment")
async def resume_payment(
    request: Request,
    telegram_id: str,
    user: User = Depends(get_admin_user)
):
    """Відновити оплату користувача"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    user_profile.paused_payment = False
    await user_profile.save()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


@app.post("/add-payment")
async def add_payment(
    request: Request,
    telegram_id: str,
    days: int = 28,
    user: User = Depends(get_admin_user)
):
    """Додати оплачені дні користувачу"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    # Якщо у користувача безлімітний тариф (-1), не змінюємо
    if user_profile.payed_days_left != -1:
        user_profile.payed_days_left += days
    
    await user_profile.save()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


@app.post("/set-unlimited")
async def set_unlimited(
    request: Request,
    telegram_id: str,
    user: User = Depends(get_admin_user)
):
    """Встановити безлімітний доступ для користувача"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    user_profile.payed_days_left = -1
    await user_profile.save()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


@app.post("/cancel-unlimited")
async def cancel_unlimited(
    request: Request,
    telegram_id: str,
    days: int = 28,
    user: User = Depends(get_admin_user)
):
    """Відмінити безлімітний доступ та встановити звичайний тариф"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    # Встановлюємо звичайний тариф з вказаною кількістю днів
    user_profile.payed_days_left = days
    await user_profile.save()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


@app.get("/morning-quiz", response_class=HTMLResponse)
async def morning_dashboard(request: Request, telegram_id: str, user: User = Depends(get_admin_user)):
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    quizzes = await MorningQuiz.find(
        MorningQuiz.user_id == telegram_id
    ).sort(-MorningQuiz.created_at).to_list()

    morning_quizes = jsonable_encoder(quizzes)

    return templates.TemplateResponse("morning_dashboard.html", {
        "request": request,
        "user": user_profile,
        "quizzes": morning_quizes,
        "current_user": user
    })


@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(
    request: Request, 
    telegram_id: str, 
    period_type: str = Query("weekly"),
    user: User = Depends(get_admin_user)
):
    """Сторінка статистики користувача"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        return templates.TemplateResponse(
            "statistics.html",
            {
                "request": request, 
                "error": f"No user with Telegram ID: {telegram_id}",
                "current_user": user
            }
        )

    return templates.TemplateResponse("statistics.html", {
        "request": request,
        "user": user_profile,
        "period_type": period_type,
        "current_user": user
    })


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request, 
    telegram_id: str, 
    user: User = Depends(get_admin_user)
):
    """Сторінка управління сповіщеннями користувача"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        return templates.TemplateResponse(
            "notifications.html",
            {
                "request": request, 
                "error": f"No user with Telegram ID: {telegram_id}",
                "current_user": user
            }
        )

    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": user_profile,
        "current_user": user
    })




@app.get("/bot-settings", response_class=HTMLResponse)
async def bot_settings_page(
    request: Request, 
    user: User = Depends(get_admin_user)
):
    """Сторінка налаштувань бота"""
    return templates.TemplateResponse("bot_settings.html", {
        "request": request,
        "current_user": user
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)