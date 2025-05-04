import json
from typing import Dict, Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.keyboards.inline import create_webapp_button
from app.models import User

# Create router
router = Router()


@router.message(Command("webapp"))
async def cmd_webapp(message: Message) -> None:
    """
    Show WebApp button
    
    Args:
        message: Telegram message
    """
    # Check if WebApp URL is using HTTPS
    if not settings.WEBAPP_URL.startswith("https://"):
        await message.answer(
            "⚠️ WebApp functionality is disabled in development mode.\n\n"
            "Telegram requires HTTPS URLs for WebApp buttons. "
            "To use WebApp features, configure an HTTPS URL in your .env file."
        )
        return
    
    await message.answer(
        "Click the button below to open our WebApp:",
        reply_markup=create_webapp_button(text="Open WebApp", path="/")
    )


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    """
    Handle data received from WebApp
    
    Args:
        message: Telegram message with web_app_data
    """
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Parse WebApp data
        try:
            data = json.loads(message.web_app_data.data)
        except json.JSONDecodeError:
            await message.answer("Invalid data received from WebApp.")
            return
        
        # Process data
        await process_webapp_data(message, data, session)
        
    except Exception as e:
        await message.answer(f"Error processing WebApp data: {str(e)}")
    finally:
        await session.close()


async def process_webapp_data(
    message: Message, 
    data: Dict[str, Any], 
    session: AsyncSession
) -> None:
    """
    Process data received from WebApp
    
    Args:
        message: Telegram message
        data: WebApp data
        session: Database session
    """
    chat_id = message.chat.id
    
    # Get user
    user = await session.get(User, message.from_user.id)
    
    if not user:
        await message.answer("Please start the bot first with /start")
        return
    
    # Example: Process form data
    if "form" in data:
        form_data = data["form"]
        
        # Store form data in user context
        if not user.context:
            user.context = {}
        
        user.context["form_data"] = form_data
        await session.commit()
        
        # Respond to user
        await message.answer(
            f"Thank you for submitting the form!\n\n"
            f"We received the following information:\n"
            f"{json.dumps(form_data, indent=2)}"
        )
    else:
        await message.answer(
            "Received data from WebApp, but no form data found."
        )
