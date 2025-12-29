from fastapi import FastAPI, Request, Query, Depends, UploadFile, File, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
import os
from datetime import datetime, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)
from app.db.database import init_db
from app.db.models import (
    User,
    TrainingSession,
    MorningQuiz,
    Notification,
    TrainingFileHistory,
    ScheduledTrainingDelivery,
    ScheduledTrainingStatus,
)
from app.constants import COUNTRIES_WITH_TIMEZONES
from typing import Optional
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from web_app.auth import verify_telegram_auth, get_current_user, serializer
from web_app.statistics_router import router as statistics_router
from web_app.notifications_router import router as notifications_router
from web_app.bot_settings_router import router as bot_settings_router
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from app.utils.training_preview import generate_training_preview_from_pdf
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles
from app.utils.training_links import (
    BadSignature,
    build_training_file_token,
    build_training_view_path,
    build_training_view_url,
    extract_training_filename,
    parse_training_file_token,
)

load_dotenv()


BOT_TOKEN = os.environ.get("BOT_TOKEN")
TG_BOT_USERNAME = os.environ.get("TG_BOT_USERNAME")
BASE_HOST = os.environ.get("BASE_HOST")

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
STATIC_DIR = Path(BASE_DIR) / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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


def _build_training_view_path(telegram_id: str, file_url: Optional[str]) -> Optional[str]:
    filename = extract_training_filename(file_url)
    if not filename:
        return None
    token = build_training_file_token(telegram_id, filename)
    return build_training_view_path(token)


def _build_training_view_url(telegram_id: str, file_url: Optional[str]) -> Optional[str]:
    filename = extract_training_filename(file_url)
    if not filename:
        return None
    token = build_training_file_token(telegram_id, filename)
    return build_training_view_url(BASE_HOST, token)


def _resolve_training_file_path(telegram_id: str, filename: str) -> Path:
    safe_filename = Path(filename).name
    return FILES_DIR / str(telegram_id) / safe_filename


def _training_file_cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,HEAD,OPTIONS",
        "Access-Control-Allow-Headers": "Range",
        "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length",
    }


@app.get("/training-file/{token}", response_class=HTMLResponse)
async def training_file_viewer(request: Request, token: str):
    try:
        data = parse_training_file_token(token)
    except BadSignature:
        raise HTTPException(status_code=404, detail="Invalid link")

    telegram_id = data.get("telegram_id")
    filename = data.get("filename")
    if not telegram_id or not filename:
        raise HTTPException(status_code=404, detail="Invalid link")

    file_path = _resolve_training_file_path(telegram_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не знайдено")

    pdf_path = f"/training-file/{token}/raw"
    base_url = BASE_HOST or str(request.base_url).rstrip("/")
    absolute_pdf_url = f"{base_url}{pdf_path}"

    user_agent = (request.headers.get("user-agent") or "").lower()
    use_google_viewer = "android" in user_agent
    viewer_url = (
        f"https://docs.google.com/gview?embedded=1&url={quote_plus(absolute_pdf_url)}"
        if use_google_viewer
        else pdf_path
    )

    return templates.TemplateResponse(
        "training_public_viewer.html",
        {
            "request": request,
            "pdf_url": pdf_path,
            "viewer_url": viewer_url,
            "filename": Path(filename).name,
        },
    )


@app.options("/training-file/{token}/raw")
async def training_file_raw_options(token: str):
    return Response(status_code=204, headers=_training_file_cors_headers())


@app.get("/training-file/{token}/raw")
async def training_file_raw(token: str):
    try:
        data = parse_training_file_token(token)
    except BadSignature:
        raise HTTPException(status_code=404, detail="Invalid link")

    telegram_id = data.get("telegram_id")
    filename = data.get("filename")
    if not telegram_id or not filename:
        raise HTTPException(status_code=404, detail="Invalid link")

    file_path = _resolve_training_file_path(telegram_id, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не знайдено")

    response_headers = _training_file_cors_headers()
    response_headers["Content-Disposition"] = f'inline; filename="{Path(filename).name}"'
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers=response_headers,
    )


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
            {
                "request": request,
                "error": f"No user with Telegram ID: {telegram_id}",
                "current_user": user,
                "countries": COUNTRIES_WITH_TIMEZONES
            }
        )

    scheduled_deliveries = await ScheduledTrainingDelivery.find(
        ScheduledTrainingDelivery.user_id == telegram_id
    ).sort("send_at").to_list()

    training_file_view_path = _build_training_view_path(
        user_profile.telegram_id,
        user_profile.training_file_url,
    )
    scheduled_view_paths = {
        item.id: _build_training_view_path(item.user_id, item.training_file_url)
        for item in scheduled_deliveries
    }
    history_items = sorted(
        user_profile.training_file_history or [],
        key=lambda item: item.sent_at,
        reverse=True,
    )
    history_view = [
        {
            "filename": item.filename,
            "sent_at": item.sent_at,
            "view_path": _build_training_view_path(
                user_profile.telegram_id, item.file_url
            ),
        }
        for item in history_items
    ]

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user_profile,
            "current_user": user,
            "countries": COUNTRIES_WITH_TIMEZONES,
            "preview_status": request.query_params.get("preview_status"),
            "preview_message": request.query_params.get("preview_message"),
            "schedule_status": request.query_params.get("schedule_status"),
            "schedule_message": request.query_params.get("schedule_message"),
            "training_status": request.query_params.get("training_status"),
            "training_message": request.query_params.get("training_message"),
            "scheduled_deliveries": scheduled_deliveries,
            "training_file_view_path": training_file_view_path,
            "scheduled_view_paths": scheduled_view_paths,
            "history_view": history_view,
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
    if not recipient:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    # Save uploads under the absolute internal files directory
    user_dir = FILES_DIR / user_telegram_id
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(file.filename).name
    file_path = user_dir / safe_filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_url = f"/files/{user_telegram_id}/{safe_filename}"

    recipient.training_file_url = file_url
    recipient.training_preview = None
    recipient.training_preview_generated_at = None
    recipient.training_preview_error = None

    preview_status = None
    preview_message = None

    try:
        preview_text = await generate_training_preview_from_pdf(content)
        recipient.training_preview = preview_text
        recipient.training_preview_generated_at = datetime.now()
        preview_status = "success"
        preview_message = "Превʼю згенеровано."
    except Exception as e:
        logger.error("Failed to generate training preview for %s: %s", user_telegram_id, e, exc_info=True)
        recipient.training_preview_error = str(e)
        preview_status = "error"
        preview_message = "Не вдалося згенерувати превʼю. Перевірте PDF або ключ OpenAI."

    await recipient.save()

    redirect_url = f"/profile?telegram_id={user_telegram_id}"
    if preview_status:
        redirect_url += f"&preview_status={preview_status}"
        if preview_message:
            redirect_url += f"&preview_message={quote_plus(preview_message)}"

    return RedirectResponse(redirect_url, status_code=302)


@app.post("/update-training-preview")
async def update_training_preview(
    request: Request,
    telegram_id: str = Form(...),
    preview_html: str = Form(""),
    user: User = Depends(get_admin_user)
):
    """Зберегти вручну відредаговане превʼю тренування."""
    recipient = await User.find_one(User.telegram_id == telegram_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    new_preview = (preview_html or "").strip()
    if not new_preview:
        redirect_url = f"/profile?telegram_id={telegram_id}&preview_status=error&preview_message={quote_plus('Превʼю не може бути порожнім.')}"
        return RedirectResponse(redirect_url, status_code=302)

    recipient.training_preview = new_preview
    recipient.training_preview_generated_at = datetime.now()
    recipient.training_preview_error = None
    await recipient.save()

    redirect_url = f"/profile?telegram_id={telegram_id}&preview_status=success&preview_message={quote_plus('Превʼю збережено.')}"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/delete-training-file")
async def delete_training_file(
    request: Request,
    telegram_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Повністю видалити файл тренування та очистити превʼю."""
    recipient = await User.find_one(User.telegram_id == telegram_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    if not recipient.training_file_url:
        redirect_url = (
            f"/profile?telegram_id={telegram_id}"
            f"&training_status=error&training_message={quote_plus('Файл тренування не призначено.')}"
        )
        return RedirectResponse(redirect_url, status_code=302)

    file_url = recipient.training_file_url
    parsed_url = urlparse(file_url)
    filename = Path(parsed_url.path).name or "training.pdf"

    file_parts = Path(parsed_url.path.lstrip("/")).parts
    if len(file_parts) >= 3 and file_parts[0] == "files":
        file_path = FILES_DIR / Path(*file_parts[1:])
        try:
            if file_path.exists():
                file_path.unlink()
                if file_path.parent.exists() and not any(file_path.parent.iterdir()):
                    file_path.parent.rmdir()
        except Exception as e:
            logger.warning(
                "Failed to delete training file from disk for %s: %s",
                telegram_id,
                e,
            )

    history_entry = TrainingFileHistory(
        filename=f"🗑️ Видалено: {filename}",
        sent_at=datetime.now(),
        file_url=None,
    )
    if not recipient.training_file_history:
        recipient.training_file_history = []
    recipient.training_file_history.append(history_entry)

    recipient.training_file_url = None
    recipient.training_preview = None
    recipient.training_preview_generated_at = None
    recipient.training_preview_error = None
    await recipient.save()

    redirect_url = (
        f"/profile?telegram_id={telegram_id}"
        f"&training_status=success&training_message={quote_plus('Файл тренування видалено.')}"
    )
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/schedule-training-delivery")
async def schedule_training_delivery(
    request: Request,
    telegram_id: str = Form(...),
    scheduled_at_kyiv: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Запланувати відправку тренування та превʼю на вказаний час (Київ)."""
    recipient = await User.find_one(User.telegram_id == telegram_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    if not recipient.training_file_url:
        redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Спочатку завантажте файл тренування.')}"
        return RedirectResponse(redirect_url, status_code=302)

    try:
        kyiv_dt_naive = datetime.strptime(scheduled_at_kyiv, "%Y-%m-%dT%H:%M")
        kyiv_dt = kyiv_dt_naive.replace(tzinfo=ZoneInfo("Europe/Kyiv"))
    except ValueError:
        redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Невірний формат дати/часу.')}"
        return RedirectResponse(redirect_url, status_code=302)

    user_offset = recipient.timezone_offset or 0
    user_local_dt = kyiv_dt + timedelta(hours=user_offset)

    file_url = recipient.training_file_url
    filename = file_url.split("/")[-1] if file_url else None

    preview_html = recipient.training_preview
    if not preview_html:
        if not filename:
            redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Не знайдено файл для генерації превʼю.')}"
            return RedirectResponse(redirect_url, status_code=302)
        file_path = FILES_DIR / telegram_id / filename
        if not file_path.exists():
            redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Файл для превʼю не знайдено на сервері.')}"
            return RedirectResponse(redirect_url, status_code=302)
        try:
            pdf_bytes = file_path.read_bytes()
            preview_html = await generate_training_preview_from_pdf(pdf_bytes)
        except Exception as e:
            logger.error("Failed to generate preview during scheduling for %s: %s", telegram_id, e, exc_info=True)
            redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Не вдалося згенерувати превʼю для розсилки.')}"
            return RedirectResponse(redirect_url, status_code=302)

    scheduled_entry = ScheduledTrainingDelivery(
        user_id=telegram_id,
        send_at=kyiv_dt,
        send_at_user_time=user_local_dt,
        training_file_url=recipient.training_file_url,
        training_preview=preview_html,
        training_filename=filename,
        status=ScheduledTrainingStatus.PENDING,
    )
    await scheduled_entry.save()

    message = f"Відправка запланована на {kyiv_dt.strftime('%Y-%m-%d %H:%M')} (Київ) / {user_local_dt.strftime('%Y-%m-%d %H:%M')} (час користувача)"
    redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=success&schedule_message={quote_plus(message)}"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/cancel-scheduled-training")
async def cancel_scheduled_training(
    request: Request,
    telegram_id: str = Form(...),
    delivery_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Скасувати заплановану відправку тренування."""
    delivery = await ScheduledTrainingDelivery.get(delivery_id)
    if not delivery or delivery.user_id != telegram_id:
        raise HTTPException(status_code=404, detail="Заплановану відправку не знайдено")

    if delivery.status != ScheduledTrainingStatus.PENDING:
        redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Можна скасувати лише заплановані (pending) відправки.')}"
        return RedirectResponse(redirect_url, status_code=302)

    delivery.status = ScheduledTrainingStatus.CANCELLED
    delivery.sent_at = datetime.now(tz=ZoneInfo("Europe/Kyiv"))
    await delivery.save()

    redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=success&schedule_message={quote_plus('Заплановану відправку скасовано.')}"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/delete-scheduled-training")
async def delete_scheduled_training(
    request: Request,
    telegram_id: str = Form(...),
    delivery_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Видалити відправку, що вже не в статусі pending."""
    delivery = await ScheduledTrainingDelivery.get(delivery_id)
    if not delivery or delivery.user_id != telegram_id:
        raise HTTPException(status_code=404, detail="Заплановану відправку не знайдено")

    if delivery.status == ScheduledTrainingStatus.PENDING:
        redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Пендінг відправки не видаляємо — спершу скасуйте.')}"
        return RedirectResponse(redirect_url, status_code=302)

    await delivery.delete()
    redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=success&schedule_message={quote_plus('Відправку видалено.')}"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/update-scheduled-preview")
async def update_scheduled_preview(
    request: Request,
    telegram_id: str = Form(...),
    delivery_id: str = Form(...),
    preview_html: str = Form(""),
    user: User = Depends(get_admin_user)
):
    """Оновити превʼю для запланованої відправки."""
    delivery = await ScheduledTrainingDelivery.get(delivery_id)
    if not delivery or delivery.user_id != telegram_id:
        raise HTTPException(status_code=404, detail="Заплановану відправку не знайдено")

    content = (preview_html or "").strip()
    if not content:
        redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=error&schedule_message={quote_plus('Превʼю не може бути порожнім.')}"
        return RedirectResponse(redirect_url, status_code=302)

    delivery.training_preview = content
    await delivery.save()

    redirect_url = f"/profile?telegram_id={telegram_id}&schedule_status=success&schedule_message={quote_plus('Превʼю оновлено для запланованої відправки.')}"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/notify-training-assigned")
async def notify_training_assigned(
    request: Request,
    telegram_id: str,
    user: User = Depends(get_admin_user)
):
    """Відправити сповіщення користувачу про присвоєне тренування"""
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    recipient = await User.find_one(User.telegram_id == telegram_id)
    if not recipient or not recipient.training_file_url:
        raise HTTPException(status_code=404, detail="Користувача не знайдено або тренування не присвоєне")
    
    # Створюємо бота
    bot = Bot(token=BOT_TOKEN)
    
    try:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Підглянути, що там", callback_data="preview_training")]
            ]
        )
        
        # Відправляємо повідомлення
        await bot.send_message(
            chat_id=int(telegram_id),
            text="🎉 Ура! Тренер оновив тобі програму. Погнали її затестимо!",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        filename = recipient.training_file_url.split("/")[-1] if recipient.training_file_url else "training.pdf"
        history_entry = TrainingFileHistory(
            filename=filename,
            sent_at=datetime.now(),
            file_url=recipient.training_file_url
        )
        if not recipient.training_file_history:
            recipient.training_file_history = []
        recipient.training_file_history.append(history_entry)
        await recipient.save()

        logger.info(f"✅ Training notification sent to user {telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send training notification to {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка відправки повідомлення: {str(e)}")
    finally:
        await bot.session.close()
    
    return RedirectResponse(f"/profile?telegram_id={telegram_id}", status_code=302)


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


@app.post("/update-timezone")
async def update_timezone(
    request: Request,
    telegram_id: str,
    country: str = Form(...),
    timezone_offset: int = Form(...),
    user: User = Depends(get_admin_user)
):
    """Оновити країну та часову зону користувача"""
    user_profile = await User.find_one(User.telegram_id == telegram_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    
    # Оновлюємо таймзону користувача
    user_profile.country = country
    user_profile.timezone_offset = timezone_offset
    await user_profile.save()
    
    # Перераховуємо всі активні сповіщення користувача на основі notification_time_base
    notifications = await Notification.find(
        Notification.user_id == telegram_id,
        Notification.is_active == True
    ).to_list()
    
    logger.info(f"🔄 Recalculating {len(notifications)} notifications for user {telegram_id} with new timezone_offset={timezone_offset}")
    
    for notification in notifications:
        if notification.notification_time_base:
            # Беремо оригінальний час користувача
            try:
                user_hour, user_minute = map(int, notification.notification_time_base.split(':'))
                
                # Конвертуємо в київський час з новим офсетом
                kyiv_hour = user_hour - timezone_offset
                
                # Обробка переходу через межу доби
                if kyiv_hour < 0:
                    kyiv_hour += 24
                elif kyiv_hour >= 24:
                    kyiv_hour -= 24
                
                notification.notification_time = f"{kyiv_hour:02d}:{user_minute:02d}"
                await notification.save()
                
                logger.info(f"✅ Updated notification {notification.id}: base={notification.notification_time_base}, kyiv={notification.notification_time}, offset={timezone_offset}")
                
            except ValueError as e:
                logger.error(f"❌ Invalid time format in notification {notification.id}: {notification.notification_time_base}, error: {e}")
                continue
    
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
