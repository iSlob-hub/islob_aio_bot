from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.utils.helpers import admin_filter, get_command_args

# Create router with admin filter
router = Router()


@router.message(Command("stats"), admin_filter)
async def cmd_stats(message: Message) -> None:
    """
    Show bot statistics (admin only)
    
    Args:
        message: Telegram message
    """
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Count total users
        stmt = select(func.count()).select_from(User)
        result = await session.execute(stmt)
        total_users = result.scalar() or 0
        
        # Get recent users (last 7 days)
        stmt = select(func.count()).select_from(User).where(
            User.created_at >= func.now() - func.interval("7 days")
        )
        result = await session.execute(stmt)
        recent_users = result.scalar() or 0
        
        stats_text = (
            f"📊 Bot Statistics\n\n"
            f"Total users: {total_users}\n"
            f"New users (last 7 days): {recent_users}\n"
        )
        
        await message.answer(stats_text)
    finally:
        await session.close()


@router.message(Command("broadcast"), admin_filter)
async def cmd_broadcast(message: Message) -> None:
    """
    Broadcast a message to all users (admin only)
    
    Args:
        message: Telegram message
    """
    args = get_command_args(message)
    
    if not args:
        await message.answer(
            "Usage: /broadcast <message>\n\n"
            "This will send the message to all registered users."
        )
        return
    
    broadcast_text = " ".join(args)
    
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Get all users
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            await message.answer("No users to broadcast to.")
            return
        
        # Send message to each user
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                await message.bot.send_message(
                    chat_id=user.chat_id,
                    text=broadcast_text
                )
                success_count += 1
            except Exception:
                fail_count += 1
        
        await message.answer(
            f"Broadcast completed.\n"
            f"✅ Sent to {success_count} users\n"
            f"❌ Failed for {fail_count} users"
        )
    finally:
        await session.close()


@router.message(Command("user"), admin_filter)
async def cmd_user_info(message: Message) -> None:
    """
    Get information about a user (admin only)
    
    Args:
        message: Telegram message
    """
    args = get_command_args(message)
    
    if not args:
        await message.answer(
            "Usage: /user <user_id>\n\n"
            "This will show information about the specified user."
        )
        return
    
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer("Invalid user ID. Must be a number.")
        return
    
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Get user
        user = await session.get(User, user_id)
        
        if not user:
            await message.answer(f"User with ID {user_id} not found.")
            return
        
        user_info = (
            f"👤 User Information\n\n"
            f"ID: {user.id}\n"
            f"Chat ID: {user.chat_id}\n"
            f"Username: {user.username or 'None'}\n"
            f"Name: {user.first_name} {user.last_name or ''}\n"
            f"Current node: {user.current_node or 'None'}\n"
            f"Created at: {user.created_at}\n"
            f"Updated at: {user.updated_at}\n"
        )
        
        await message.answer(user_info)
    finally:
        await session.close()
