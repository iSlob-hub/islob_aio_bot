import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.user import (
    create_user,
    get_user_by_id,
    get_user_by_chat_id,
    update_user,
    update_user_node,
)


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession):
    """Test creating a user."""
    user_data = {
        "id": 987654321,
        "chat_id": 987654321,
        "username": "new_user",
        "first_name": "New",
        "last_name": "User",
    }
    
    user = await create_user(session, user_data)
    
    assert user.id == user_data["id"]
    assert user.chat_id == user_data["chat_id"]
    assert user.username == user_data["username"]
    assert user.first_name == user_data["first_name"]
    assert user.last_name == user_data["last_name"]


@pytest.mark.asyncio
async def test_get_user_by_id(session: AsyncSession, test_user: User):
    """Test getting a user by ID."""
    user = await get_user_by_id(session, test_user.id)
    
    assert user is not None
    assert user.id == test_user.id
    assert user.chat_id == test_user.chat_id
    assert user.username == test_user.username


@pytest.mark.asyncio
async def test_get_user_by_chat_id(session: AsyncSession, test_user: User):
    """Test getting a user by chat ID."""
    user = await get_user_by_chat_id(session, test_user.chat_id)
    
    assert user is not None
    assert user.id == test_user.id
    assert user.chat_id == test_user.chat_id
    assert user.username == test_user.username


@pytest.mark.asyncio
async def test_update_user(session: AsyncSession, test_user: User):
    """Test updating a user."""
    user_data = {
        "username": "updated_user",
        "first_name": "Updated",
    }
    
    updated_user = await update_user(session, test_user, user_data)
    
    assert updated_user.id == test_user.id
    assert updated_user.chat_id == test_user.chat_id
    assert updated_user.username == user_data["username"]
    assert updated_user.first_name == user_data["first_name"]
    assert updated_user.last_name == test_user.last_name


@pytest.mark.asyncio
async def test_update_user_node(session: AsyncSession, test_user: User):
    """Test updating a user's conversation node."""
    new_node = "welcome"
    context = {"last_action": "greeting"}
    
    updated_user = await update_user_node(session, test_user, new_node, context)
    
    assert updated_user.id == test_user.id
    assert updated_user.current_node == new_node
    assert updated_user.context is not None
    assert updated_user.context.get("last_action") == "greeting"
