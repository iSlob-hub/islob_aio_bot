from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Dict, Any, Callable, Awaitable
from app.db.models import ConversationTransition
import datetime


class ConversationTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        state = data.get("state")
        if state:
            prev_state = await state.get_state()
            result = await handler(event, data)
            current_state = await state.get_state()

            if prev_state and current_state:
                prev_group = prev_state.split(":")[0]
                current_group = current_state.split(":")[0]

                if prev_group != current_group:
                    user_id = (
                        event.from_user.id
                        if hasattr(event, "from_user")
                        else event.message.from_user.id
                    )
                    conversation_transition = ConversationTransition(
                        user_id=str(user_id),
                        from_flow=prev_group,
                        to_flow=current_group,
                        timestamp=datetime.datetime.now(),
                    )
                    await conversation_transition.insert()

            return result
        return await handler(event, data)
