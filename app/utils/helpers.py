from typing import List, Union

from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings


def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        bool: True if user is an admin, False otherwise
    """
    return user_id in settings.ADMIN_USER_IDS


def admin_filter(message: Message) -> bool:
    """
    Filter for admin-only commands
    
    Args:
        message: Telegram message
        
    Returns:
        bool: True if user is an admin, False otherwise
    """
    return is_admin(message.from_user.id)


def extract_user_data(user: types.User) -> dict:
    """
    Extract user data from Telegram User object
    
    Args:
        user: Telegram User object
        
    Returns:
        dict: User data
    """
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def get_command_args(message: Message) -> List[str]:
    """
    Extract command arguments from message
    
    Args:
        message: Telegram message
        
    Returns:
        List[str]: Command arguments
    """
    command_parts = message.text.split()
    return command_parts[1:] if len(command_parts) > 1 else []
