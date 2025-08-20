import os
import sys
import json
import http.server
import socketserver
import decimal
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add the parent directory to sys.path to import modules from the main project
sys.path.append(str(Path(__file__).parent.parent))

# Import our modules
from utils.logger import get_logger
from generate_web_data import get_statistics_data, generate_data_file, generate_html_from_data

# Configure logger
logger = get_logger(__name__)

# Define the port to run the server on
PORT = 8000

# Get the directory of this script
BASE_DIR = Path(__file__).parent

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class StatisticsHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for statistics web server"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        logger.debug(f"Received request: {path} with params: {query_params}")
        
        # Serve static files
        if path == "/" or path == "/index.html":
            self.serve_index_page()
        elif path == "/api/stats":
            self.serve_stats_api(query_params)
        elif path == "/stats.html":
            self.serve_stats_page(query_params)
        else:
            # Check if it's a static file
            requested_file = self.translate_path(self.path)
            if os.path.exists(requested_file) and os.path.isfile(requested_file):
                logger.debug(f"Serving static file: {requested_file}")
                # Serve static files
                super().do_GET()
            else:
                logger.warning(f"File not found: {requested_file}")
                self.send_error(404, f"File not found: {self.path}")
    
    def serve_index_page(self):
        """Serve the main index page"""
        logger.info("Serving index page")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        index_path = os.path.join(BASE_DIR, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "rb") as f:
                content = f.read()
                self.wfile.write(content)
                logger.debug(f"Served index.html, size: {len(content)} bytes")
        else:
            error_msg = f"Index file not found at {index_path}"
            logger.error(error_msg)
            self.wfile.write(error_msg.encode())
    
    def serve_stats_api(self, query_params):
        """Serve statistics data as JSON"""
        try:
            # Get parameters
            user_id = int(query_params.get("user_id", [7])[0])  # Default user_id = 7
            
            # Get date range parameters
            start_date = query_params.get("start_date", [None])[0]
            end_date = query_params.get("end_date", [None])[0]
            period = query_params.get("period", [None])[0]  # Now optional
            
            logger.info(f"Generating API data for user_id={user_id}, period={period}, start_date={start_date}, end_date={end_date}")
            
            # Generate statistics data
            data = get_statistics_data(user_id, start_date, end_date, period)
            
            # Send response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            # Send JSON data
            json_data = json.dumps(data, cls=DecimalEncoder)
            self.wfile.write(json_data.encode())
            logger.debug(f"Served API data, size: {len(json_data)} bytes")
            
        except Exception as e:
            logger.exception(f"Error serving stats API: {str(e)}")
            self.send_error(500, str(e))
    
    def serve_stats_page(self, query_params):
        """Generate and serve a statistics HTML page"""
        try:
            # Get parameters
            user_id = int(query_params.get("user_id", [7])[0])  # Default user_id = 7
            
            # Get date range parameters
            start_date = query_params.get("start_date", [None])[0]
            end_date = query_params.get("end_date", [None])[0]
            period = query_params.get("period", [None])[0]  # Now optional
            
            logger.info(f"Generating stats page for user_id={user_id}, period={period}, start_date={start_date}, end_date={end_date}")
            
            # Generate data file
            data_file = generate_data_file(user_id, start_date, end_date, period)
            
            if data_file:
                # Generate HTML
                html_file = generate_html_from_data(data_file)
                
                # Serve the HTML file
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                with open(html_file, "rb") as f:
                    content = f.read()
                    self.wfile.write(content)
                    logger.debug(f"Served stats HTML, size: {len(content)} bytes")
            else:
                error_msg = "Could not generate statistics data"
                logger.error(error_msg)
                self.send_error(404, error_msg)
                
        except Exception as e:
            logger.exception(f"Error serving stats page: {str(e)}")
            self.send_error(500, str(e))


def run_server():
    """Run the web server"""
    handler = StatisticsHandler
    
    # Set the directory to serve files from
    os.chdir(BASE_DIR)
    
    # Create the server
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        server_url = f"http://localhost:{PORT}"
        logger.info(f"Server running at {server_url}")
        print(f"Server running at {server_url}")
        print("Available endpoints:")
        print(f"  - {server_url}/ - Main page")
        print(f"  - {server_url}/stats.html?user_id=7&period=weekly - Generated statistics page (weekly)")
        print(f"  - {server_url}/stats.html?user_id=7&start_date=2025-03-01&end_date=2025-03-30 - Custom date range")
        print(f"  - {server_url}/api/stats?user_id=7&period=monthly - JSON API endpoint (monthly)")
        print(f"  - {server_url}/api/stats?user_id=7&start_date=2025-03-01&end_date=2025-03-30 - JSON API with custom dates")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped")
            print("\nServer stopped")


if __name__ == "__main__":
    run_server()
