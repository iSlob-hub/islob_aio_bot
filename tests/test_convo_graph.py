import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.convo_graph import ConversationGraph, Node
from app.models import User


@pytest.mark.asyncio
async def test_conversation_graph_initialization():
    """Test initializing the conversation graph."""
    graph = ConversationGraph()
    
    assert graph.nodes == {}
    assert graph.initial_node is None


@pytest.mark.asyncio
async def test_add_node():
    """Test adding a node to the graph."""
    graph = ConversationGraph()
    
    # Create a mock handler
    async def mock_handler(*args, **kwargs):
        return True
    
    # Create a node
    node = Node(
        name="test_node",
        handler=mock_handler,
        transitions={"next": "next_node"}
    )
    
    # Add the node to the graph
    graph.add_node(node)
    
    assert "test_node" in graph.nodes
    assert graph.nodes["test_node"] == node


@pytest.mark.asyncio
async def test_set_initial_node():
    """Test setting the initial node."""
    graph = ConversationGraph()
    
    # Create a mock handler
    async def mock_handler(*args, **kwargs):
        return True
    
    # Create a node
    node = Node(
        name="start_node",
        handler=mock_handler,
    )
    
    # Add the node to the graph
    graph.add_node(node)
    
    # Set the initial node
    graph.set_initial_node("start_node")
    
    assert graph.initial_node == "start_node"


@pytest.mark.asyncio
async def test_process_update(session: AsyncSession, test_user: User):
    """Test processing an update through the graph."""
    graph = ConversationGraph()
    
    # Create mock handlers
    async def start_handler(*args, **kwargs):
        return "next"
    
    async def welcome_handler(*args, **kwargs):
        return True
    
    # Create mock enter/exit actions
    async def on_enter(*args, **kwargs):
        pass
    
    async def on_exit(*args, **kwargs):
        pass
    
    # Create nodes
    start_node = Node(
        name="start",
        handler=start_handler,
        transitions={"next": "welcome"},
        on_exit=on_exit
    )
    
    welcome_node = Node(
        name="welcome",
        handler=welcome_handler,
        on_enter=on_enter
    )
    
    # Add nodes to the graph
    graph.add_node(start_node)
    graph.add_node(welcome_node)
    graph.set_initial_node("start")
    
    # Create a mock update
    update = MagicMock()
    update.message = AsyncMock(spec=Message)
    update.message.from_user = AsyncMock(spec=TelegramUser)
    
    # Set user's current node
    test_user.current_node = "start"
    await session.commit()
    
    # Process the update
    result = await graph.process_update(update, test_user, session)
    
    # Check that the update was processed and the node was changed
    assert result is True
    assert test_user.current_node == "welcome"


@pytest.mark.asyncio
async def test_process_update_no_transition(session: AsyncSession, test_user: User):
    """Test processing an update with no transition."""
    graph = ConversationGraph()
    
    # Create mock handler that doesn't trigger a transition
    async def mock_handler(*args, **kwargs):
        return True  # Return True but not a transition key
    
    # Create a node
    node = Node(
        name="test_node",
        handler=mock_handler,
        transitions={"next": "next_node"}
    )
    
    # Add the node to the graph
    graph.add_node(node)
    graph.set_initial_node("test_node")
    
    # Create a mock update
    update = MagicMock()
    
    # Set user's current node
    test_user.current_node = "test_node"
    await session.commit()
    
    # Process the update
    result = await graph.process_update(update, test_user, session)
    
    # Check that the update was processed but the node wasn't changed
    assert result is True
    assert test_user.current_node == "test_node"
