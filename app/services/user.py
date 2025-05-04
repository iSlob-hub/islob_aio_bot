from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user_by_id(
    session: AsyncSession, 
    user_id: int
) -> Optional[User]:
    """
    Get a user by ID
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    return await session.get(User, user_id)


async def get_user_by_chat_id(
    session: AsyncSession, 
    chat_id: int
) -> Optional[User]:
    """
    Get a user by chat ID
    
    Args:
        session: Database session
        chat_id: Chat ID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    stmt = select(User).where(User.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    user_data: dict
) -> User:
    """
    Create a new user
    
    Args:
        session: Database session
        user_data: User data
        
    Returns:
        User: Created user
    """
    user = User(**user_data)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    user_data: dict
) -> User:
    """
    Update a user
    
    Args:
        session: Database session
        user: User to update
        user_data: User data
        
    Returns:
        User: Updated user
    """
    for key, value in user_data.items():
        setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_users(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[User]:
    """
    Get all users with pagination
    
    Args:
        session: Database session
        limit: Maximum number of users to return
        offset: Number of users to skip
        
    Returns:
        List[User]: List of users
    """
    stmt = select(User).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_user_node(
    session: AsyncSession,
    user: User,
    node_name: str,
    context: Optional[dict] = None
) -> User:
    """
    Update a user's conversation node
    
    Args:
        session: Database session
        user: User to update
        node_name: Node name
        context: Optional context data
        
    Returns:
        User: Updated user
    """
    user.current_node = node_name
    
    if context is not None:
        if user.context is None:
            user.context = {}
        user.context.update(context)
    
    await session.commit()
    await session.refresh(user)
    return user
