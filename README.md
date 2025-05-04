# islob_aio_bot

{{ ... }}

# Telegram Bot Boilerplate

A comprehensive Python Telegram bot boilerplate using Aiogram 3.x with async SQLAlchemy and PostgreSQL.

## Features

- **Aiogram 3.x** with long-polling
- **Async SQLAlchemy ORM** with PostgreSQL
- **Pydantic BaseSettings** for configuration
- **Alembic** for database migrations
- **APScheduler** for scheduling follow-up messages
- **Conversation Graph Engine** for managing dialog flows
- **Telegram Web App** integration
- **Docker** multi-service setup
- **Pytest** examples for testing

## Project Structure

```
├── app/
│ ├── __init__.py
│ ├── main.py                  # sets up Bot & Dispatcher, calls start_polling
│ ├── config.py                # Pydantic settings
│ ├── db.py                    # async engine, sessionmaker
│ ├── models/                  # SQLAlchemy models
│ │ ├── __init__.py
│ │ └── user.py               # User model with chat_id
│ ├── handlers/                # Aiogram handlers
│ │ ├── __init__.py
│ │ ├── start.py              # /start, register & save chat_id
│ │ ├── webapp.py             # Telegram.WebApp launch & data handling
│ │ └── admin.py              # admin-only commands
│ ├── services/                # business logic & CRUD
│ │ ├── __init__.py
│ │ └── user.py               # User service
│ ├── keyboards/               # InlineKeyboard & WebAppKeyboardButton helpers
│ │ ├── __init__.py
│ │ └── inline.py             # Inline keyboard builders
│ ├── scheduler.py             # APScheduler setup & example follow-up job
│ ├── convo_graph.py           # directed‐graph conversation engine
│ ├── webapp/                  # WebApp server
│ │ ├── __init__.py
│ │ └── server.py             # FastAPI server for WebApp
│ └── utils/                   # logging, validators, helpers
│   ├── __init__.py
│   ├── logging.py            # Logging configuration
│   └── helpers.py            # Helper functions
├── webapp/                    # mini-app code
│ ├── static/                  # CSS, JS, images
│ └── templates/               # HTML templates
├── tests/                     # pytest async test examples
│ ├── __init__.py
│ ├── conftest.py             # Test fixtures
│ ├── test_services.py        # Service tests
│ └── test_convo_graph.py     # Conversation graph tests
├── migrations/                # Alembic migrations
│ ├── env.py
│ ├── script.py.mako
│ └── versions/
│   └── initial_migration.py  # Initial database schema
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── .env.example
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Docker and Docker Compose (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/islob_aio_bot.git
   cd islob_aio_bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your configuration:
   ```
   BOT_TOKEN=your_bot_token_here
   ADMIN_USER_IDS=123456789,987654321
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bot_db
   WEBAPP_URL=http://localhost:8000
   ```

### Running with Docker

1. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

2. Check the logs:
   ```bash
   docker-compose logs -f bot
   ```

### Running Locally

1. Start PostgreSQL:
   ```bash
   docker-compose up -d db
   ```

2. Apply migrations:
   ```bash
   alembic upgrade head
   ```

3. Run the bot:
   ```bash
   python -m app.main
   ```

## Scheduling Follow-up Messages

The bot includes an APScheduler setup for scheduling follow-up messages to users. Here's an example of how to use it:

```python
from app.scheduler import schedule_follow_up

# Schedule a follow-up message to be sent 2 days later
await schedule_follow_up(
    bot=bot,
    chat_id=user.chat_id,
    delay_days=2,
    message="How are you enjoying our bot? Any feedback for us?",
    context={"user_id": user.id}
)
```

## Conversation Graph Engine

The conversation graph engine allows you to define a directed graph of conversation states and transitions between them. Each node in the graph represents a state in the conversation and has a handler function that processes updates in that state.

### Example Usage

```python
from app.convo_graph import Node, conversation_graph

# Define node handlers
async def start_node_handler(update, user, session, context):
    await update.message.answer("Welcome! What would you like to do?")
    return "next"

async def menu_node_handler(update, user, session, context):
    # Process user input and return transition key
    return "option1"

# Create nodes
start_node = Node(
    name="start",
    handler=start_node_handler,
    transitions={"next": "menu"}
)

menu_node = Node(
    name="menu",
    handler=menu_node_handler,
    transitions={"option1": "option1_node", "option2": "option2_node"}
)

# Add nodes to the graph
conversation_graph.add_node(start_node)
conversation_graph.add_node(menu_node)
conversation_graph.set_initial_node("start")
```

## WebApp Integration

The bot includes a WebApp integration that allows you to create mini-apps that run inside Telegram. The WebApp server is built with FastAPI and serves static files and HTML templates.

### Example Usage

```python
from app.keyboards.inline import create_webapp_button

# Show WebApp button
await message.answer(
    "Click the button below to open our WebApp:",
    reply_markup=create_webapp_button(text="Open WebApp", path="/")
)
```

## Testing

Run the tests with pytest:

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.