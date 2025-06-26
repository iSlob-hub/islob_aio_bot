from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union
from app.db.models import User


class VerifiedUserFilter(Filter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        user = await User.find_one(User.telegram_id == str(message.from_user.id))
        if user and user.is_active:
            return True
        return False
