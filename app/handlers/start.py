from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.convo_graph import conversation_graph
from app.db import get_session
from app.models import User
from app.scheduler import schedule_example_follow_up
from app.utils.helpers import extract_user_data

# Create router
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Handle /start command
    
    Args:
        message: Telegram message
    """
    user_data = extract_user_data(message.from_user)
    chat_id = message.chat.id
    
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Check if user exists
        stmt = select(User).where(User.chat_id == chat_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                id=user_data["id"],
                chat_id=chat_id,
                username=user_data["username"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                current_node="start",  # Set initial conversation node
            )
            session.add(user)
            await session.commit()
            
            await message.answer(
                f"Welcome, {user.first_name}! This is your first time using our bot."
            )
            
            # Schedule a follow-up message for 2 days later
            await schedule_example_follow_up(message.bot, user)
            
        else:
            # Update user data if needed
            user.username = user_data["username"]
            user.first_name = user_data["first_name"]
            user.last_name = user_data["last_name"]
            await session.commit()
            
            await message.answer(
                f"Welcome back, {user.first_name}! How can I help you today?"
            )
        
        # Process through conversation graph
        if user.current_node:
            await conversation_graph.process_update(
                message, user, session, context={}
            )
        else:
            # Set initial node if not set
            user.current_node = "start"
            await session.commit()
            
    except Exception as e:
        await message.answer(f"An error occurred: {str(e)}")
    finally:
        await session.close()


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """
    Reset user's conversation state
    
    Args:
        message: Telegram message
    """
    chat_id = message.chat.id
    
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Get user
        stmt = select(User).where(User.chat_id == chat_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Reset conversation state
            user.current_node = "start"
            user.context = {}
            await session.commit()
            
            await message.answer("Your conversation has been reset.")
        else:
            await message.answer("You need to start the bot first with /start")
    finally:
        await session.close()
