import os
import tempfile
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from loguru import logger

template_dir = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(template_dir))

async def capture_statistics_image(stats_data, output_path=None, template_name="template.html"):
    """
    Generate a statistics image using Playwright and the existing template
    
    Args:
        stats_data (dict): Dictionary containing statistics data
        output_path (str, optional): Path to save the output image. If None, a temporary file is created.
        template_name (str): Name of the template file to use
        
    Returns:
        str: Path to the generated image
    """
    # If no output path is provided, create a temporary file
    if output_path is None:
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "statistics_image.png")
    
    # Create a temporary HTML file from the template
    template = env.get_template(template_name)
    html_content = template.render(charts=stats_data, user={"name": "Training Stats"})
    
    temp_html_path = os.path.join(os.path.dirname(output_path), "temp_stats.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Use Playwright to capture a screenshot
    try:
        logger.info("Launching Playwright")
        async with async_playwright() as p:
            # Check if we're on Heroku
            on_heroku = os.environ.get("DYNO") is not None
            
            # Configure browser launch options based on environment
            launch_options = {
                "args": ["--no-sandbox", "--disable-setuid-sandbox"],
                "headless": True
            }
            
            # Add specific options for Heroku
            if on_heroku:
                logger.info("Running on Heroku, using special configuration")
                # Force using installed browser if available
                if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.heroku/python/lib/python3.13/site-packages/playwright/driver/package/.local-browsers"
                
                # Additional args for Heroku
                launch_options["args"].extend([
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ])
            
            # Launch browser with configured options
            logger.info(f"Launching browser with options: {launch_options}")
            browser = await p.chromium.launch(**launch_options)
            
            # Create a new page
            page = await browser.new_page(viewport={"width": 1200, "height": 1600})
            
            # Navigate to the HTML file (using proper file:// URL format)
            file_url = f"file://{os.path.abspath(temp_html_path)}"
            logger.info(f"Navigating to: {file_url}")
            await page.goto(file_url)
            
            # Wait for charts to render (adjust timeout as needed)
            await page.wait_for_timeout(2000)  # 2 seconds
            
            # Take a screenshot
            logger.info(f"Taking screenshot and saving to: {output_path}")
            await page.screenshot(path=output_path, full_page=True)
            
            # Close the browser
            await browser.close()
    except Exception as e:
        logger.error(f"Error in Playwright screenshot capture: {e}")
        # Create a directory for the output path if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create a simple fallback image with text
        try:
            from PIL import Image, ImageDraw
            
            # Create a blank image with white background
            img = Image.new('RGB', (800, 600), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            
            # Add text
            d.text((50, 50), "Statistics Image Generation Failed", fill=(0, 0, 0))
            d.text((50, 100), f"Error: {str(e)}", fill=(255, 0, 0))
            d.text((50, 150), "Please try again later.", fill=(0, 0, 0))
            
            # Save the image
            img.save(output_path)
            logger.info(f"Created fallback image at {output_path}")
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback image: {fallback_error}")
            return None
    
    # Clean up the temporary HTML file
    try:
        os.remove(temp_html_path)
    except Exception as e:
        logger.warning(f"Failed to remove temporary HTML file: {e}")
    
    return output_path
