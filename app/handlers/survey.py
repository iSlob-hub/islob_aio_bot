"""
Survey command handler
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.survey import register_survey_conversation
from app.db import get_session
from app.models import User

# Create router
router = Router()

# Register survey conversation nodes
register_survey_conversation()


@router.message(Command("survey"))
async def cmd_survey(message: Message) -> None:
    """
    Start the survey conversation
    
    Args:
        message: Telegram message
    """
    chat_id = message.chat.id
    
    # Get database session
    session: AsyncSession = await get_session()
    
    try:
        # Get user
        user = await session.get(User, message.from_user.id)
        
        if not user:
            await message.answer(
                "Please start the bot first with /start command."
            )
            return
        
        # Set user's current node to the survey start node
        user.current_node = "survey_start"
        await session.commit()
        
        # Process the message through the conversation graph
        from app.convo_graph import conversation_graph
        await conversation_graph.process_update(message, user, session, context={})
        
    except Exception as e:
        await message.answer(f"An error occurred: {str(e)}")
    finally:
        await session.close()
