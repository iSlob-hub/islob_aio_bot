from typing import List, Optional, Union

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings


def create_inline_keyboard(
    buttons: List[List[dict]],
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard from a list of button data
    
    Args:
        buttons: List of button rows, each containing button data
            Each button dict should have 'text' and one of:
            - 'callback_data'
            - 'url'
            - 'web_app'
            
    Returns:
        InlineKeyboardMarkup: Inline keyboard
    """
    builder = InlineKeyboardBuilder()
    
    for row in buttons:
        row_buttons = []
        for button in row:
            text = button["text"]
            
            if "callback_data" in button:
                row_buttons.append(
                    InlineKeyboardButton(text=text, callback_data=button["callback_data"])
                )
            elif "url" in button:
                row_buttons.append(
                    InlineKeyboardButton(text=text, url=button["url"])
                )
            elif "web_app" in button:
                web_app_url = button.get("web_app_url") or f"{settings.WEBAPP_URL}{button['web_app']}"
                row_buttons.append(
                    InlineKeyboardButton(
                        text=text, 
                        web_app=WebAppInfo(url=web_app_url)
                    )
                )
        
        if row_buttons:
            builder.row(*row_buttons)
    
    return builder.as_markup()


def create_webapp_button(
    text: str = "Open WebApp",
    path: str = "/",
    url: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """
    Create a keyboard with a WebApp button
    
    Args:
        text: Button text
        path: WebApp path
        url: Optional custom URL
        
    Returns:
        InlineKeyboardMarkup: Inline keyboard with WebApp button
    """
    web_app_url = url or f"{settings.WEBAPP_URL}{path}"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=text,
            web_app=WebAppInfo(url=web_app_url)
        )
    )
    
    return builder.as_markup()
