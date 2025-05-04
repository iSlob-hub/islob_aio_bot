from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Union

from aiogram import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@dataclass
class Node:
    """Represents a node in the conversation graph"""
    name: str
    handler: Callable
    transitions: Dict[str, str] = field(default_factory=dict)
    
    # Optional entry and exit actions
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None


class ConversationGraph:
    """Directed graph for managing conversation flow"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.initial_node: Optional[str] = None
    
    def add_node(self, node: Node) -> None:
        """Add a node to the graph"""
        self.nodes[node.name] = node
    
    def set_initial_node(self, node_name: str) -> None:
        """Set the initial node for new conversations"""
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} does not exist")
        self.initial_node = node_name
    
    async def process_update(
        self, 
        update: types.Update, 
        user: User, 
        session: AsyncSession,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Process an update through the conversation graph
        
        Args:
            update: The Telegram update
            user: The user model
            session: Database session
            context: Optional context data
            
        Returns:
            bool: True if the update was handled, False otherwise
        """
        if not context:
            context = {}
        
        # Get current node or use initial node
        current_node_name = user.current_node or self.initial_node
        if not current_node_name:
            return False
        
        current_node = self.nodes.get(current_node_name)
        if not current_node:
            return False
        
        # Process the update with the current node's handler
        result = await current_node.handler(update, user, session, context)
        
        # Check if we need to transition
        if isinstance(result, str) and result in current_node.transitions:
            next_node_name = current_node.transitions[result]
            next_node = self.nodes.get(next_node_name)
            
            if next_node:
                # Execute exit action if defined
                if current_node.on_exit:
                    await current_node.on_exit(user, session, context)
                
                # Update user's current node
                user.current_node = next_node_name
                await session.commit()
                
                # Execute enter action if defined
                if next_node.on_enter:
                    await next_node.on_enter(user, session, context)
                
                return True
        
        return bool(result)


# Create the conversation graph instance
conversation_graph = ConversationGraph()


# Example node handlers
async def start_node_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> str:
    """Example handler for the start node"""
    # Process update and return transition key
    return "next"


async def welcome_node_handler(
    update: types.Update, 
    user: User, 
    session: AsyncSession,
    context: Dict[str, Any]
) -> Union[str, bool]:
    """Example handler for the welcome node"""
    # Process update and return transition key or boolean
    return True


# Example node setup
start_node = Node(
    name="start",
    handler=start_node_handler,
    transitions={"next": "welcome"}
)

welcome_node = Node(
    name="welcome",
    handler=welcome_node_handler,
    transitions={}
)

# Configure the graph
conversation_graph.add_node(start_node)
conversation_graph.add_node(welcome_node)
conversation_graph.set_initial_node("start")
