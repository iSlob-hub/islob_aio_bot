"""
Module for generating statistics web visualizations from the current data models
"""

import os
import json
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Union, Any
from jinja2 import Environment, FileSystemLoader
import logging

from app.db.models import UserStatistics, PeriodType
from app.config import settings

logger = logging.getLogger(__name__)

# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
# Create the templates directory if it doesn't exist
TEMPLATES_DIR.mkdir(exist_ok=True)

class WebStatisticsGenerator:
    """Generate web-based statistics visualizations from UserStatistics model"""
    
    def __init__(self):
        # Create a Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        
        # Ensure the template exists
        template_path = TEMPLATES_DIR / "statistics_template.html"
        if not template_path.exists():
            logger.info("Statistics template not found, creating it")
            self._create_template()
    
    def _create_template(self):
        """Create the HTML template for statistics visualization"""
        template_path = TEMPLATES_DIR / "statistics_template.html"
        
        # Copy the template from the new_statistics_template.html if it exists
        new_template = Path(__file__).parent.parent / "templates" / "new_statistics_template.html"
        if new_template.exists():
            logger.info(f"Copying template from {new_template}")
            with open(new_template, "r", encoding="utf-8") as src, \
                 open(template_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        else:
            # Copy from the statistics_web directory if it exists
            statistics_web_template = Path(__file__).parent.parent / "statistics_web" / "template.html"
            if statistics_web_template.exists():
                logger.info(f"Copying template from {statistics_web_template}")
                with open(statistics_web_template, "r", encoding="utf-8") as src, \
                     open(template_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            else:
                # Create a minimal template
                logger.info("Creating minimal statistics template")
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write("""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Статистика тренувань</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --stress-color: #e7c60f;
            --hardness-color: #FF0000;
            --sleep-color: #9370DB;
            --feelings-color: #289828;
            --weight-color: #00BFFF;
            --background-color: #87bbd2;
            --card-background: #FFFFFF;
            --card-shadow: 0 4px 12px rgba(108, 170, 199, 0.519);
            --border-radius: 20px;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            background-color: var(--background-color);
            margin: 0;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            grid-template-rows: auto auto auto;
            gap: 25px;
        }
        
        .stats-card {
            background-color: var(--card-background);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            aspect-ratio: 1 / 1;
        }
        
        .stats-card.wide {
            grid-column: span 2;
            aspect-ratio: 2 / 1;
        }
        
        .card-header {
            padding: 15px;
            text-align: center;
            color: white;
            font-weight: bold;
            border-radius: 30px;
            margin: 15px auto 10px;
            width: 85%;
            max-width: 220px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .card-header h2 {
            margin: 0;
            font-size: 22px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        
        .card-body {
            padding: 15px;
            flex-grow: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .chart-container {
            width: 100%;
            height: 100%;
            position: relative;
            padding: 10px;
            box-sizing: border-box;
        }
        
        /* Card header colors */
        .stress { background-color: var(--stress-color); }
        .hardness { background-color: var(--hardness-color); }
        .sleep { background-color: var(--sleep-color); }
        .feelings { background-color: var(--feelings-color); }
        .weight { background-color: var(--weight-color); }
    </style>
</head>
<body>
    <div class="container">
        <div class="stats-grid" id="statsGrid">
            <!-- Стрес -->
            <div class="stats-card">
                <div class="card-header stress">
                    <h2><b>СТРЕС</b></h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="stressChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Складність -->
            <div class="stats-card">
                <div class="card-header hardness">
                    <h2><b>СКЛАДНІСТЬ</b></h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="hardnessChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Сон -->
            <div class="stats-card">
                <div class="card-header sleep">
                    <h2><b>СОН</b></h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="sleepChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Самопочуття -->
            <div class="stats-card">
                <div class="card-header feelings">
                    <h2><b>САМОПОЧУТТЯ</b></h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="feelingsChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Вага -->
            <div class="stats-card wide">
                <div class="card-header weight">
                    <h2><b>ВАГА</b></h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="weightChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Data from Python
        const sampleData = {{ charts|tojson }};
        
        // Console logging for debugging
        console.log("Chart data loaded:", sampleData);
        
        // Set default Chart.js options
        Chart.defaults.font.family = "'Arial', sans-serif";
        Chart.defaults.font.size = 14;
        Chart.defaults.font.weight = 'bold';
        Chart.defaults.color = '#000000';
        
        // Common chart options
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleFont: { size: 16, weight: 'bold' },
                    bodyFont: { size: 14, weight: 'bold' },
                    padding: 10,
                    cornerRadius: 5,
                    displayColors: false
                }
            },
            layout: {
                padding: { left: 20, right: 20, top: 20, bottom: 20 }
            },
            scales: {
                x: {
                    grid: {
                        display: true,
                        color: 'rgba(200, 200, 200, 0.15)',
                        borderDash: [5, 5],
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 10 },
                        color: '#888',
                        maxRotation: 0,
                        padding: 5
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        display: true,
                        color: 'rgba(200, 200, 200, 0.15)',
                        borderDash: [5, 5],
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 10 },
                        color: '#888',
                        padding: 5,
                        stepSize: 1
                    }
                }
            },
            elements: {
                point: { radius: 6, hoverRadius: 8, borderWidth: 0 },
                line: { tension: 0.4, borderWidth: 3 },
                bar: { borderWidth: 0, borderRadius: 4 }
            }
        };

        // Function to display "No data" message in center of chart
        function displayNoDataMessage(chart, datasetLabel) {
            const ctx = chart.ctx;
            const width = chart.width;
            const height = chart.height;
            
            chart.clear();
            
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.font = 'bold 16px Arial';
            ctx.fillStyle = '#666';
            ctx.fillText(`Немає даних про ${datasetLabel}`, width / 2, height / 2);
            ctx.restore();
        }

        // Function to create a chart with no data handling
        function createChart(ctx, config, datasetLabel) {
            const chart = new Chart(ctx, config);
            
            // Check if there's no data
            if (!config.data.datasets[0].data.length) {
                displayNoDataMessage(chart, datasetLabel);
            }
            
            return chart;
        }

        // Create stress chart (line chart with yellow line)
        const stressCtx = document.getElementById('stressChart').getContext('2d');
        const stressGradient = stressCtx.createLinearGradient(0, 0, 0, 300);
        stressGradient.addColorStop(0, 'rgba(255, 215, 0, 0.1)');
        stressGradient.addColorStop(1, 'rgba(255, 215, 0, 0.0)');
        
        const stressConfig = {
            type: 'line',
            data: {
                labels: sampleData.dates,
                datasets: [{
                    data: sampleData.stress.values,
                    borderColor: '#FFD700', // Yellow
                    backgroundColor: stressGradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#FFD700',
                    pointBorderColor: '#FFD700',
                    pointHoverBackgroundColor: '#FFD700',
                    pointHoverBorderColor: '#FFD700',
                    tension: 0.4,
                    fill: true,
                    spanGaps: true
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        min: 0,
                        max: 10.5,
                        ticks: {
                            ...commonOptions.scales.y.ticks,
                            stepSize: 2
                        }
                    }
                }
            }
        };
        const stressChart = createChart(stressCtx, stressConfig, 'рівень стресу');

        // Create hardness chart
        const hardnessCtx = document.getElementById('hardnessChart').getContext('2d');
        const hardnessGradient = hardnessCtx.createLinearGradient(0, 0, 0, 300);
        hardnessGradient.addColorStop(0, 'rgba(255, 0, 0, 0.3)');
        hardnessGradient.addColorStop(1, 'rgba(255, 0, 0, 0.0)');
        
        const hardnessConfig = {
            type: 'line',
            data: {
                labels: sampleData.dates,
                datasets: [{
                    data: sampleData.hardness.values,
                    borderColor: '#FF0000', // Red
                    backgroundColor: hardnessGradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#FF0000',
                    pointBorderColor: '#FF0000',
                    pointHoverBackgroundColor: '#FF0000',
                    pointHoverBorderColor: '#FF0000',
                    tension: 0.4,
                    fill: true,
                    spanGaps: true
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        min: 0,
                        max: 10.5,
                        ticks: {
                            ...commonOptions.scales.y.ticks,
                            stepSize: 2
                        }
                    }
                }
            }
        };
        const hardnessChart = createChart(hardnessCtx, hardnessConfig, 'складність тренувань');

        // Create sleep chart
        const sleepCtx = document.getElementById('sleepChart').getContext('2d');
        const sleepConfig = {
            type: 'bar',
            data: {
                labels: sampleData.dates,
                datasets: [{
                    data: sampleData.sleep.values,
                    backgroundColor: '#9370DB', // Purple
                    borderColor: '#9370DB',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        min: 0,
                        max: 12,
                        ticks: {
                            ...commonOptions.scales.y.ticks,
                            stepSize: 2
                        }
                    }
                }
            }
        };
        const sleepChart = createChart(sleepCtx, sleepConfig, 'години сну');

        // Create feelings chart
        const feelingsCtx = document.getElementById('feelingsChart').getContext('2d');
        const feelingsGradient = feelingsCtx.createLinearGradient(0, 0, 0, 300);
        feelingsGradient.addColorStop(0, 'rgba(0, 255, 0, 0.1)');
        feelingsGradient.addColorStop(1, 'rgba(0, 255, 0, 0.0)');
        
        const feelingsConfig = {
            type: 'line',
            data: {
                labels: sampleData.dates,
                datasets: [{
                    data: sampleData.feelings.values,
                    borderColor: '#00FF00', // Green
                    backgroundColor: feelingsGradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#00FF00',
                    pointBorderColor: '#00FF00',
                    pointHoverBackgroundColor: '#00FF00',
                    pointHoverBorderColor: '#00FF00',
                    tension: 0.4,
                    fill: true,
                    spanGaps: true
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        min: 0,
                        max: 10.5,
                        ticks: {
                            ...commonOptions.scales.y.ticks,
                            stepSize: 2
                        }
                    }
                }
            }
        };
        const feelingsChart = createChart(feelingsCtx, feelingsConfig, 'самопочуття');

        // Create weight chart
        const weightCtx = document.getElementById('weightChart').getContext('2d');
        const weightGradient = weightCtx.createLinearGradient(0, 0, 0, 300);
        weightGradient.addColorStop(0, 'rgba(0, 191, 255, 0.6)');
        weightGradient.addColorStop(0.5, 'rgba(0, 191, 255, 0.3)');
        weightGradient.addColorStop(1, 'rgba(0, 191, 255, 0.0)');
        
        const weightConfig = {
            type: 'line',
            data: {
                labels: sampleData.dates,
                datasets: [{
                    label: 'Вага',
                    data: sampleData.weight.values,
                    borderColor: '#00BFFF', // Deep Sky Blue
                    backgroundColor: weightGradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#00BFFF',
                    pointBorderColor: '#00BFFF',
                    pointHoverBackgroundColor: '#00BFFF',
                    pointHoverBorderColor: '#00BFFF',
                    tension: 0.4,
                    fill: true,
                    spanGaps: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: false,
                            text: 'Вага (кг)'
                        }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        };
        
        const weightChart = createChart(weightCtx, weightConfig, 'Вага');
    </script>
</body>
</html>""")
    
    def _convert_statistics_to_chart_data(self, stats: UserStatistics) -> Dict[str, Any]:
        """Convert UserStatistics model to chart data format for template"""
        # Extract all dates from the data points in each category
        all_dates = set()
        
        # Process stress data
        stress_data = {}
        if stats.stress_data and "data_points" in stats.stress_data:
            for point in stats.stress_data["data_points"]:
                date = point.get("date", "")
                if date:
                    all_dates.add(date)
                    stress_data[date] = point.get("value")
        
        # Process hardness (warehouse) data
        hardness_data = {}
        if stats.warehouse_data and "data_points" in stats.warehouse_data:
            for point in stats.warehouse_data["data_points"]:
                date = point.get("date", "")
                if date:
                    all_dates.add(date)
                    hardness_data[date] = point.get("value")
        
        # Process sleep data
        sleep_data = {}
        if stats.sleep_data and "data_points" in stats.sleep_data:
            for point in stats.sleep_data["data_points"]:
                date = point.get("date", "")
                if date:
                    all_dates.add(date)
                    sleep_data[date] = point.get("value")
        
        # Process wellbeing (feelings) data
        feelings_data = {}
        if stats.wellbeing_data and "data_points" in stats.wellbeing_data:
            for point in stats.wellbeing_data["data_points"]:
                date = point.get("date", "")
                if date:
                    all_dates.add(date)
                    feelings_data[date] = point.get("value")
        
        # Process weight data
        weight_data = {}
        if stats.weight_data and "data_points" in stats.weight_data:
            for point in stats.weight_data["data_points"]:
                date = point.get("date", "")
                if date:
                    all_dates.add(date)
                    weight_data[date] = point.get("value")
        
        # Sort all dates
        sorted_dates = sorted(all_dates)
        
        # Create arrays for chart data with matching dates
        stress_values = [stress_data.get(date) for date in sorted_dates]
        hardness_values = [hardness_data.get(date) for date in sorted_dates]
        sleep_values = [sleep_data.get(date) for date in sorted_dates]
        feelings_values = [feelings_data.get(date) for date in sorted_dates]
        weight_values = [weight_data.get(date) for date in sorted_dates]
        
        # Create the chart data structure
        chart_data = {
            "dates": sorted_dates,
            "stress": {
                "values": stress_values,
                "color": "#FFD700"  # Yellow for stress
            },
            "hardness": {
                "values": hardness_values,
                "color": "#FF0000"  # Red for hardness
            },
            "sleep": {
                "values": sleep_values,
                "color": "#9370DB"  # Purple for sleep
            },
            "feelings": {
                "values": feelings_values,
                "color": "#00FF00"  # Green for feelings
            },
            "weight": {
                "values": weight_values,
                "color": "#00BFFF"  # Blue for weight
            }
        }
        
        return chart_data
    
    async def generate_html(self, stats: UserStatistics, output_path: Optional[str] = None) -> str:
        """
        Generate HTML for statistics visualization
        
        Args:
            stats: UserStatistics model
            output_path: Path to save the output HTML file
            
        Returns:
            Path to the generated HTML file
        """
        # Convert statistics to chart data
        chart_data = self._convert_statistics_to_chart_data(stats)
        
        # Get the template
        template = self.env.get_template("new_statistics_template.html")
        
        # Render the template
        html_content = template.render(charts=chart_data)
        
        # Save the HTML file if output_path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return output_path
        else:
            # Create a temporary file
            fd, temp_path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(html_content)
            return temp_path
    
    async def generate_image(self, stats: UserStatistics, output_path: Optional[str] = None) -> str:
        """
        Generate a statistics image from UserStatistics model
        
        Args:
            stats: UserStatistics model
            output_path: Path to save the output image file
            
        Returns:
            Path to the generated image file
        """
        from playwright.async_api import async_playwright
        
        # Generate HTML
        html_path = await self.generate_html(stats)
        
        # Set default output path if not provided
        if output_path is None:
            # Generate output filename based on user_id and period type
            period_text = "weekly" if stats.period_type == PeriodType.WEEKLY else "monthly"
            period_end = stats.period_end
            if isinstance(period_end, str):
                period_end = datetime.fromisoformat(period_end)
            
            filename = f"{stats.user_id}_{period_text}_{period_end.strftime('%Y%m%d')}.png"
            
            # Create the statistics_images directory if it doesn't exist
            images_dir = Path(__file__).parent.parent / "statistics_images"
            os.makedirs(images_dir, exist_ok=True)
            
            output_path = images_dir / filename
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Capture screenshot with playwright
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                    headless=True
                )
                
                # Create a new page with fixed size
                page = await browser.new_page(viewport={"width": 1200, "height": 1600})
                
                # Navigate to the HTML file
                file_url = f"file://{os.path.abspath(html_path)}"
                await page.goto(file_url)
                
                # Wait for charts to render
                await page.wait_for_timeout(2000)  # 2 seconds should be enough
                
                # Take a screenshot
                await page.screenshot(path=output_path, full_page=True)
                
                # Close the browser
                await browser.close()
            
            logger.info(f"Generated statistics image: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error generating statistics image: {e}")
            return None
        finally:
            # Clean up the temporary HTML file
            try:
                os.remove(html_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary HTML file: {e}")


# Test function to generate a statistics image from an existing UserStatistics object
async def generate_test_image(user_id: str = None, period_type: str = "weekly") -> str:
    """Generate a test statistics image"""
    from app.db.database import init_db
    from app.db.models import UserStatistics, PeriodType
    
    # Initialize database connection
    await init_db()
    
    # Get a statistics object
    period = PeriodType.WEEKLY if period_type.lower() == "weekly" else PeriodType.MONTHLY
    
    # Find the statistics object
    query = {}
    if user_id:
        query["user_id"] = user_id
    query["period_type"] = period
    
    stats = await UserStatistics.find_one(query)
    
    if not stats:
        logger.error(f"No statistics found for user_id={user_id}, period_type={period_type}")
        return None
    
    # Generate the image
    generator = WebStatisticsGenerator()
    image_path = await generator.generate_image(stats)
    
    return image_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate statistics images")
    parser.add_argument("--user-id", type=str, help="User ID to generate statistics for")
    parser.add_argument("--period", type=str, default="weekly", choices=["weekly", "monthly"], 
                        help="Period for statistics (weekly or monthly)")
    
    args = parser.parse_args()
    
    # Run the test function
    image_path = asyncio.run(generate_test_image(args.user_id, args.period))
    if image_path:
        print(f"Generated statistics image: {image_path}")
    else:
        print("Failed to generate statistics image")
