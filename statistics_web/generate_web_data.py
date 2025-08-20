import os
import sys
import json
import datetime
import decimal
from pathlib import Path
import pandas as pd

# Add the parent directory to sys.path to import modules from the main project
sys.path.append(str(Path(__file__).parent.parent))

from database import get_db
from models import User
from statistics_3 import BaseStatisticsRecord, WeeklyStatisticsRecord, MonthlyStatisticsRecord
from utils.logger import get_logger

# Configure logger
logger = get_logger(__name__)

# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, datetime.datetime) or isinstance(obj, datetime.time):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)


def format_date(dt):
    """Format datetime to DD.MM format for x-axis labels"""
    if dt is None:
        return None
    return dt.strftime("%d.%m")


def prepare_chart_data(df, value_column):
    """
    Convert DataFrame with dt and value columns to chart-friendly format
    Returns a dict with dates and values arrays
    """
    if not isinstance(df, pd.DataFrame):
        logger.warning(f"Expected pandas DataFrame, got {type(df)}")
        return {"dates": [], "values": []}
        
    if df.empty:
        return {"dates": [], "values": []}
    
    # Sort by date in chronological order (ascending)
    df = df.sort_values("dt")
    
    # Create a list of (datetime, formatted_date, value) tuples to maintain the connection
    # between the original datetime and the formatted string
    data_points = [(dt, format_date(dt), val) for dt, val in zip(df["dt"], df[value_column])]
    
    # Don't reverse the order - we want oldest dates on the right
    # (This is already in chronological order from the sort_values above)
    
    # Extract the formatted dates and values while maintaining their connection
    dates = [point[1] for point in data_points]
    values = [point[2] for point in data_points]
    
    return {
        "dates": dates,
        "values": values
    }


def get_statistics_data(user_id, start_date=None, end_date=None, period=None):
    """
    Extract statistics data for a specific user and date range
    Returns data formatted for web visualization
    
    Parameters:
    - user_id: User ID to get statistics for
    - start_date: Start date (datetime or string in format YYYY-MM-DD)
    - end_date: End date (datetime or string in format YYYY-MM-DD)
    - period: Predefined period ("weekly", "monthly") - only used if start_date and end_date are None
    """
    session = next(get_db())
    
    # Get user information
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User with ID {user_id} not found")
        return {"error": f"User with ID {user_id} not found"}
    
    user_full_name = user.full_name or f"User {user_id}"
    
    # Parse dates if they are strings
    if isinstance(start_date, str):
        try:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            logger.error("Invalid start_date format. Use YYYY-MM-DD.")
            return {"error": "Invalid start_date format. Use YYYY-MM-DD."}
    
    if isinstance(end_date, str):
        try:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            logger.error("Invalid end_date format. Use YYYY-MM-DD.")
            return {"error": "Invalid end_date format. Use YYYY-MM-DD."}
    
    # Create appropriate statistics record based on input
    if start_date and end_date:
        logger.info(f"Creating custom date range statistics for user {user_id} from {start_date} to {end_date}")
        stats = BaseStatisticsRecord(session, user_id, start_date, end_date, user_full_name)
        period_type = "custom"
    elif period:
        # Predefined period
        if period.lower() == "weekly":
            logger.info(f"Creating weekly statistics for user {user_id}")
            stats = WeeklyStatisticsRecord(session, user_id, user_full_name=user_full_name)
            period_type = "weekly"
        elif period.lower() == "monthly":
            logger.info(f"Creating monthly statistics for user {user_id}")
            stats = MonthlyStatisticsRecord(session, user_id, user_full_name=user_full_name)
            period_type = "monthly"
        else:
            logger.error(f"Invalid period: {period}. Use 'weekly' or 'monthly'.")
            return {"error": f"Invalid period: {period}. Use 'weekly' or 'monthly'."}
    else:
        # Default to weekly if no dates or period specified
        logger.info(f"Creating weekly statistics for user {user_id}")
        stats = WeeklyStatisticsRecord(session, user_id, user_full_name=user_full_name)
        period_type = "weekly"
    
    # Get all the required data
    stress_df = stats.get_stress_data()
    sleep_df = stats.get_sleeping_hours_data()
    hardness_df = stats.get_training_hardness_data()
    feelings_df = stats.get_feelings_data()
    soreness_df = stats.get_soreness_data()
    weight_df = stats.get_weight_data()  # Add weight data retrieval
    
    # Process soreness data to match the format needed for visualization
    soreness_dates = soreness_df["dt"].tolist() if not soreness_df.empty else []
    
    # Prepare data for charts
    stress_data = prepare_chart_data(stress_df, "stress")
    sleep_data = prepare_chart_data(sleep_df, "hours")
    hardness_data = prepare_chart_data(hardness_df, "hardness")
    feelings_data = prepare_chart_data(feelings_df, "feelings")
    weight_data = prepare_chart_data(weight_df, "weight")  # Process weight data
    
    # Create soreness markers array that matches hardness dates
    soreness_markers = []
    if not hardness_df.empty and soreness_dates:
        for dt in hardness_df["dt"]:
            soreness_markers.append(dt in soreness_dates)
    elif not hardness_df.empty:
        # If no soreness data, create array of False values with same length as hardness data
        soreness_markers = [False] * len(hardness_df)
    
    # Get summary metrics
    trainings_count = stats.get_trainings_count()
    avg_hardness = stats.get_average_training_hardness()
    avg_stress = stats.get_average_stress()
    
    # Get all unique dates from all datasets to create a complete date array
    all_dates_with_dt = []
    
    for df in [stress_df, sleep_df, hardness_df, feelings_df, weight_df]:  # Add weight_df
        if not df.empty:
            for dt in df["dt"]:
                formatted_date = format_date(dt)
                # Store both the original datetime and the formatted string
                all_dates_with_dt.append((dt, formatted_date))
    
    # Remove duplicates while preserving the datetime-string connection
    unique_dates = {}
    for dt, formatted_date in all_dates_with_dt:
        unique_dates[formatted_date] = dt
    
    # Sort the dates chronologically by the original datetime, then reverse to show newest first
    all_dates_with_dt = [(dt, formatted) for formatted, dt in unique_dates.items()]
    all_dates_with_dt.sort(key=lambda x: x[0])  # Sort by datetime, oldest first
    
    # Extract just the formatted dates for display
    all_dates = [date_tuple[1] for date_tuple in all_dates_with_dt]
    
    # Create arrays with values for each date, using null for missing values
    stress_values = []
    hardness_values = []
    sleep_values = []
    feelings_values = []
    weight_values = []  # Add weight values array
    soreness_array = []
    
    # Map of date strings to original datetime objects for soreness checking
    hardness_date_map = {}
    if not hardness_df.empty:
        for i, dt in enumerate(hardness_df["dt"]):
            hardness_date_map[format_date(dt)] = dt
    
    # Fill in values for each date
    for date in all_dates:
        # Stress values
        if date in stress_data["dates"]:
            idx = stress_data["dates"].index(date)
            stress_values.append(stress_data["values"][idx])
        else:
            stress_values.append(None)
        
        # Hardness values
        if date in hardness_data["dates"]:
            idx = hardness_data["dates"].index(date)
            hardness_values.append(hardness_data["values"][idx])
            
            # Check if this date has soreness
            if hardness_date_map.get(date) in soreness_dates:
                soreness_array.append(True)
            else:
                soreness_array.append(False)
        else:
            hardness_values.append(None)
            soreness_array.append(False)
        
        # Sleep values
        if date in sleep_data["dates"]:
            idx = sleep_data["dates"].index(date)
            sleep_values.append(sleep_data["values"][idx])
        else:
            sleep_values.append(None)
        
        # Feelings values
        if date in feelings_data["dates"]:
            idx = feelings_data["dates"].index(date)
            feelings_values.append(feelings_data["values"][idx])
        else:
            feelings_values.append(None)
            
        # Weight values
        if date in weight_data["dates"]:
            idx = weight_data["dates"].index(date)
            weight_values.append(weight_data["values"][idx])
        else:
            weight_values.append(None)
    
    # Compile all data in the format expected by charts.js
    web_data = {
        "user": {
            "id": user_id,
            "name": user_full_name
        },
        "period": {
            "type": period_type,
            "start_date": format_date(stats.start_date),
            "end_date": format_date(stats.end_date)
        },
        "metrics": {
            "trainings_count": trainings_count,
            "avg_hardness": round(avg_hardness, 1) if avg_hardness else 0,
            "avg_stress": round(avg_stress, 1) if avg_stress else 0
        },
        "charts": {
            "dates": all_dates,
            "stress": {
                "values": stress_values,
                "color": "#FFD700"  # Yellow
            },
            "hardness": {
                "values": hardness_values,
                "color": "#FF0000",  # Red
                "soreness": soreness_array
            },
            "sleep": {
                "values": sleep_values,
                "color": "#9370DB"  # Purple
            },
            "feelings": {
                "values": feelings_values,
                "color": "#00FF00"  # Green
            },
            "weight": {
                "values": weight_values,
                "color": "#00BFFF"  # Blue
            }
        }
    }
    
    return web_data


def generate_data_file(user_id, start_date=None, end_date=None, period=None, output_path=None):
    """
    Generate a JavaScript file with statistics data for web visualization
    
    Parameters:
    - user_id: User ID to get statistics for
    - start_date: Start date (datetime or string in format YYYY-MM-DD)
    - end_date: End date (datetime or string in format YYYY-MM-DD)
    - period: Predefined period ("weekly", "monthly") - only used if start_date and end_date are None
    - output_path: Path to save the output file (default: data.js in current directory)
    """
    logger.info(f"Generating data file for user {user_id}")
    data = get_statistics_data(user_id, start_date, end_date, period)
    
    if "error" in data:
        logger.error(f"Error: {data['error']}")
        return None
    
    # Default output path
    if output_path is None:
        output_dir = Path(__file__).parent
        output_path = output_dir / "data.js"
    
    # Format the data exactly as expected by the existing charts.js
    # The existing charts.js expects a specific structure with 'sampleData'
    charts_data = {
        "dates": data["charts"]["dates"],
        "stress": {
            "values": data["charts"]["stress"]["values"],
            "color": data["charts"]["stress"]["color"]
        },
        "hardness": {
            "values": data["charts"]["hardness"]["values"],
            "color": data["charts"]["hardness"]["color"],
            "soreness": data["charts"]["hardness"]["soreness"]
        },
        "sleep": {
            "values": data["charts"]["sleep"]["values"],
            "color": data["charts"]["sleep"]["color"]
        },
        "feelings": {
            "values": data["charts"]["feelings"]["values"],
            "color": data["charts"]["feelings"]["color"]
        },
        "weight": {
            "values": data["charts"]["weight"]["values"],
            "color": data["charts"]["weight"]["color"]
        }
    }
    
    logger.debug(f"Generated charts_data structure: {json.dumps(charts_data, cls=DecimalEncoder)[:500]}...")
    
    # Generate JavaScript file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("// Generated statistics data\n")
        f.write(f"// User: {data['user']['name']}, Period: {data['period']['type']}\n")
        f.write(f"// From {data['period']['start_date']} to {data['period']['end_date']}\n\n")
        f.write("const sampleData = ")
        json_data = json.dumps(charts_data, indent=2, ensure_ascii=False, cls=DecimalEncoder)
        f.write(json_data)
        f.write(";\n")
        
        logger.debug(f"Written to {output_path}: const sampleData = {json_data[:500]}...")
    
    # Also generate a JSON file for potential use by other tools
    json_path = str(output_path).replace(".js", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
    
    logger.info(f"Generated data files at:\n- {output_path}\n- {json_path}")
    return output_path


def generate_html_from_data(data_path, template_path=None, output_path=None, for_image=False):
    """
    Generate HTML file from data using Jinja2 templating
    
    Parameters:
    - data_path: Path to the data file (.js or .json) or a dictionary containing the data directly
    - template_path: Path to the template file (default: template.html)
    - output_path: Path to save the output HTML file (default: stats.html)
    - for_image: If True, use a different output path (stats_image.html)
    
    Returns:
    - If output_path is provided: Path to the generated HTML file
    - If output_path is None: HTML content as a string
    """
    import json
    import os
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader

    logger = get_logger(__name__)

    # Load data
    base_dir = Path(__file__).parent
    
    # Check if data_path is already a dictionary (direct data)
    if isinstance(data_path, dict):
        logger.info("Using provided dictionary data directly")
        data = data_path
    else:
        # Handle file paths
        if isinstance(data_path, str):
            data_path = Path(data_path)
        logger.debug(f"DATA PATH: {data_path}")
        
        try:
            if data_path.suffix == '.js':
                # If data_path is a .js file, convert to .json path
                json_path = data_path.with_suffix('.json')
                logger.info(f"Using JSON data from: {json_path}")
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                # Assume it's a .json file
                logger.info(f"Using JSON data from: {data_path}")
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except AttributeError:
            logger.error(f"Invalid data path: {data_path}")
            raise ValueError(f"Data path must be a Path object, string path, or dictionary. Got: {type(data_path)}")
    
    # Set default paths if not provided
    if template_path is None:
        template_path = base_dir / "template.html"
    
    if output_path is None:
        if for_image:
            output_path = base_dir / "stats_image.html"
        else:
            output_path = base_dir / "stats.html"
    
    logger.info(f"Template path: {template_path}, Output path: {output_path}")
    
    # Check if template exists
    if not os.path.exists(template_path):
        logger.error(f"Template not found at: {template_path}")
        raise FileNotFoundError(f"Template file not found: {template_path}")
    else:
        logger.info(f"Using existing template: {template_path}")
        # Log the first few lines of the template
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
            logger.debug(f"Template first 200 chars: {template_content[:200]}...")
    
    # Setup Jinja environment with custom filters
    env = Environment(loader=FileSystemLoader(base_dir))
    
    # Add custom filter to format dates
    def format_date_filter(value, format='%d.%m.%Y'):
        if isinstance(value, str):
            try:
                value = datetime.datetime.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(value, datetime.datetime):
            return value.strftime(format)
        return value
    
    # Add custom filter to convert to JSON
    def tojson_filter(value):
        json_str = json.dumps(value, cls=DecimalEncoder)
        logger.debug(f"tojson filter output (first 200 chars): {json_str[:200]}...")
        return json_str
    
    env.filters['format_date'] = format_date_filter
    env.filters['tojson'] = tojson_filter
    
    logger.info(f"Jinja environment set up with filters: {list(env.filters.keys())}")
    
    try:
        template = env.get_template(os.path.basename(template_path))
        logger.info(f"Successfully loaded template: {os.path.basename(template_path)}")
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        raise
    
    # Format the charts data to match the expected structure for the template
    charts_data = {
        "dates": data["charts"]["dates"],
        "stress": {
            "values": data["charts"]["stress"]["values"],
            "color": data["charts"]["stress"]["color"]
        },
        "hardness": {
            "values": data["charts"]["hardness"]["values"],
            "color": data["charts"]["hardness"]["color"],
            "soreness": data["charts"]["hardness"]["soreness"]
        },
        "sleep": {
            "values": data["charts"]["sleep"]["values"],
            "color": data["charts"]["sleep"]["color"]
        },
        "feelings": {
            "values": data["charts"]["feelings"]["values"],
            "color": data["charts"]["feelings"]["color"]
        },
        "weight": {
            "values": data["charts"]["weight"]["values"],
            "color": data["charts"]["weight"]["color"]
        }
    }
    
    logger.debug(f"Template charts_data: {json.dumps(charts_data, cls=DecimalEncoder)[:500]}...")
    
    # Render template with data
    try:
        logger.info("Rendering template with data...")
        html_content = template.render(
            user=data["user"],
            period=data["period"],
            metrics=data["metrics"],
            charts=charts_data
        )
        logger.info(f"Template rendered successfully, HTML size: {len(html_content)} bytes")
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise
    
    # Check if the HTML contains the expected JavaScript
    if 'const sampleData' in html_content:
        logger.info("HTML contains 'const sampleData' declaration - good!")
        # Find the sampleData declaration
        start_idx = html_content.find('const sampleData')
        end_idx = html_content.find('</script>', start_idx)
        if start_idx > 0 and end_idx > start_idx:
            js_snippet = html_content[start_idx:end_idx]
            logger.debug(f"Found sampleData declaration: {js_snippet[:200]}...")
        else:
            logger.warning("Could not extract sampleData declaration")
    else:
        logger.error("HTML does NOT contain 'const sampleData' declaration - this is a problem!")
    
    # Write output file
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML file at: {output_path}")
        
        # Debug HTML file is only created if DEBUG_HTML environment variable is set
        if os.environ.get("DEBUG_HTML"):
            # Write a debug copy with line numbers
            debug_output_path = str(output_path).replace(".html", "_debug.html")
            with open(debug_output_path, "w", encoding="utf-8") as f:
                lines = html_content.split("\n")
                for i, line in enumerate(lines):
                    f.write(f"{i+1:04d}: {line}\n")
            
            logger.info(f"Generated debug HTML file with line numbers at: {debug_output_path}")
        
        return output_path
    else:
        return html_content


def inspect_charts_js_compatibility():
    """
    Inspect the charts.js file to understand what data structure it expects
    and compare it with our generated data
    """
    charts_js_path = os.path.join(Path(__file__).parent, "charts.js")
    if not os.path.exists(charts_js_path):
        logger.error(f"Charts.js file not found at {charts_js_path}")
        return
    
    logger.info(f"Inspecting charts.js file at {charts_js_path}")
    
    with open(charts_js_path, "r", encoding="utf-8") as f:
        charts_js_content = f.read()
    
    # Look for variable declarations
    var_declarations = []
    for line in charts_js_content.split("\n"):
        if "const " in line and " = " in line:
            var_declarations.append(line.strip())
    
    logger.info(f"Found variable declarations in charts.js: {var_declarations[:5]}")
    
    # Check for sampleData references
    sample_data_refs = []
    for line in charts_js_content.split("\n"):
        if "sampleData" in line:
            sample_data_refs.append(line.strip())
    
    logger.info(f"Found sampleData references in charts.js: {sample_data_refs[:5]}")
    
    # Check data structure in our generated file
    data_js_path = os.path.join(Path(__file__).parent, "data.js")
    if os.path.exists(data_js_path):
        with open(data_js_path, "r", encoding="utf-8") as f:
            data_js_content = f.read()
        
        # Extract the sampleData structure
        if "const sampleData = " in data_js_content:
            data_structure = data_js_content.split("const sampleData = ")[1].split(";\n")[0]
            logger.info(f"Our generated data structure: {data_structure[:500]}...")
        else:
            logger.error("Could not find 'const sampleData = ' in data.js")
    else:
        logger.error(f"Data.js file not found at {data_js_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate statistics data for web visualization")
    parser.add_argument("--user-id", type=int, required=True, help="User ID to generate statistics for")
    parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--period", type=str, default=None, choices=["weekly", "monthly"], 
                        help="Period for statistics (weekly or monthly)")
    parser.add_argument("--output-dir", type=str, default=None, 
                        help="Output directory for generated files (default: current directory)")
    
    args = parser.parse_args()
    
    # Set output paths
    output_dir = args.output_dir or Path(__file__).parent
    data_path = os.path.join(output_dir, "data.js")
    template_path = os.path.join(output_dir, "template.html")
    html_path = os.path.join(output_dir, "stats.html")
    
    # Generate data file
    data_file = generate_data_file(args.user_id, args.start_date, args.end_date, args.period, data_path)
    
    if data_file:
        # Generate HTML from data
        generate_html_from_data(data_file, template_path, html_path)
    
    # Inspect charts.js compatibility
    inspect_charts_js_compatibility()