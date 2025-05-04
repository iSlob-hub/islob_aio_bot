import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings

# Create FastAPI app
app = FastAPI(title="Telegram WebApp")

# Get base directory
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "webapp" / "templates"
STATIC_DIR = BASE_DIR / "webapp" / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Server instance
server_instance: Optional[uvicorn.Server] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render index page
    
    Args:
        request: FastAPI request
        
    Returns:
        HTMLResponse: Rendered HTML
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Telegram WebApp"}
    )


@app.get("/api/config")
async def get_config():
    """
    Get WebApp configuration
    
    Returns:
        dict: Configuration data
    """
    return {
        "version": "1.0.0",
        "features": ["form", "chat"],
    }


async def start_webapp_server() -> None:
    """
    Start the WebApp server
    """
    global server_instance
    
    # Create templates directory if it doesn't exist
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    
    # Create static directory if it doesn't exist
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # Create default index.html if it doesn't exist
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>Telegram WebApp</h1>
        <p>This is a Telegram WebApp example.</p>
        
        <form id="dataForm">
            <div class="form-group">
                <label for="name">Name:</label>
                <input type="text" id="name" name="name" required>
            </div>
            
            <div class="form-group">
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="form-group">
                <label for="message">Message:</label>
                <textarea id="message" name="message" rows="4" required></textarea>
            </div>
            
            <button type="submit" id="submitButton">Submit</button>
        </form>
    </div>
    
    <script src="/static/js/app.js"></script>
</body>
</html>""")
    
    # Create default CSS file if it doesn't exist
    css_dir = STATIC_DIR / "css"
    os.makedirs(css_dir, exist_ok=True)
    css_path = css_dir / "style.css"
    if not css_path.exists():
        with open(css_path, "w") as f:
            f.write("""body {
    font-family: 'Roboto', Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: var(--tg-theme-bg-color, #f5f5f5);
    color: var(--tg-theme-text-color, #222);
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    color: var(--tg-theme-button-color, #2481cc);
    text-align: center;
    margin-bottom: 20px;
}

.form-group {
    margin-bottom: 15px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

input, textarea {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: var(--tg-theme-secondary-bg-color, #fff);
    color: var(--tg-theme-text-color, #222);
}

button {
    background-color: var(--tg-theme-button-color, #2481cc);
    color: var(--tg-theme-button-text-color, #fff);
    border: none;
    padding: 12px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
    width: 100%;
    margin-top: 10px;
}

button:hover {
    opacity: 0.9;
}""")
    
    # Create default JS file if it doesn't exist
    js_dir = STATIC_DIR / "js"
    os.makedirs(js_dir, exist_ok=True)
    js_path = js_dir / "app.js"
    if not js_path.exists():
        with open(js_path, "w") as f:
            f.write("""// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand the WebApp to full height
tg.expand();

// Set the main button color
tg.MainButton.setParams({
    text: 'Submit Form',
    color: tg.themeParams.button_color,
    text_color: tg.themeParams.button_text_color,
});

// Handle form submission
document.getElementById('dataForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    // Get form data
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;
    
    // Create data object
    const formData = {
        name: name,
        email: email,
        message: message
    };
    
    // Send data back to Telegram
    tg.sendData(JSON.stringify({
        form: formData
    }));
    
    // Close the WebApp
    tg.close();
});

// Show main button when form is valid
function checkFormValidity() {
    const form = document.getElementById('dataForm');
    if (form.checkValidity()) {
        tg.MainButton.show();
    } else {
        tg.MainButton.hide();
    }
}

// Check form validity on input
const formInputs = document.querySelectorAll('input, textarea');
formInputs.forEach(input => {
    input.addEventListener('input', checkFormValidity);
});

// Initial check
checkFormValidity();

// Handle main button click
tg.MainButton.onClick(function() {
    document.getElementById('submitButton').click();
});""")
    
    # Check if WebApp URL is using HTTPS
    if not settings.WEBAPP_URL.startswith("https://"):
        logging.warning(
            "⚠️ WebApp URL is not using HTTPS. Telegram requires HTTPS URLs for WebApp buttons. "
            "The WebApp functionality will be disabled in the bot interface."
        )
        logging.info(
            "💡 Tip: For local development, you can use a service like ngrok to create a secure tunnel "
            "to your local server. Example: ngrok http 8000"
        )
    
    # Configure and start the server
    config = uvicorn.Config(
        app=app,
        host=settings.WEBAPP_HOST,
        port=settings.WEBAPP_PORT,
        log_level="info",
    )
    
    server = uvicorn.Server(config)
    server_instance = server
    
    # Run the server in a separate task
    asyncio.create_task(server.serve())
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    logging.info(f"WebApp server started at {settings.WEBAPP_URL}")
    if settings.WEBAPP_URL.startswith("https://"):
        logging.info("WebApp functionality is enabled")
    else:
        logging.info("WebApp functionality is disabled in the bot interface")


async def stop_webapp_server() -> None:
    """
    Stop the WebApp server
    """
    global server_instance
    
    if server_instance:
        server_instance.should_exit = True
        await asyncio.sleep(0.5)  # Give the server time to shut down
        server_instance = None
