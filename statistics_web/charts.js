// Common chart options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: {
            display: false
        },
        tooltip: {
            enabled: false
        }
    },
    layout: {
        padding: 0
    },
    scales: {
        x: {
            grid: {
                color: 'rgba(200, 200, 200, 0.2)',
                borderDash: [5, 5],
                drawBorder: false
            },
            ticks: {
                font: {
                    size: 8
                },
                color: '#888',
                callback: function(value, index) {
                    // Only show every 4th label to avoid crowding
                    return index % 4 === 0 ? this.getLabelForValue(value) : '';
                },
                padding: 0
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(200, 200, 200, 0.2)',
                borderDash: [5, 5],
                drawBorder: false
            },
            ticks: {
                font: {
                    size: 8
                },
                color: '#888',
                stepSize: 1,
                padding: 0
            }
        }
    },
    elements: {
        point: {
            radius: 3,
            hoverRadius: 3
        },
        line: {
            tension: 0.5 // Increased tension for more rounded lines
        }
    }
};

// Create stress chart (line chart)
const stressCtx = document.getElementById('stressChart').getContext('2d');
const stressChart = new Chart(stressCtx, {
    type: 'line',
    data: {
        labels: sampleData.dates,
        datasets: [{
            label: 'Стрес',
            data: sampleData.stress.values,
            backgroundColor: 'rgba(255, 215, 0, 0.0)',
            borderColor: sampleData.stress.color,
            borderWidth: 2,
            pointBackgroundColor: sampleData.stress.color,
            pointBorderColor: sampleData.stress.color,
            pointBorderWidth: 0,
            pointRadius: 3,
            tension: 0.5, // More rounded line
            fill: false,
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
                max: 8,
                ticks: {
                    ...commonOptions.scales.y.ticks,
                    stepSize: 1
                }
            }
        }
    }
});

// Create hardness chart (line chart with red background)
const hardnessCtx = document.getElementById('hardnessChart').getContext('2d');

// Create gradient for hardness chart
const hardnessGradient = hardnessCtx.createLinearGradient(0, 0, 0, 300);
hardnessGradient.addColorStop(0, 'rgba(255, 0, 0, 0.1)');
hardnessGradient.addColorStop(1, 'rgba(255, 0, 0, 0.0)');

const hardnessChart = new Chart(hardnessCtx, {
    type: 'line',
    data: {
        labels: sampleData.dates,
        datasets: [{
            label: 'Складність',
            data: sampleData.hardness.values,
            backgroundColor: hardnessGradient,
            borderColor: sampleData.hardness.color,
            borderWidth: 2,
            pointBackgroundColor: sampleData.hardness.color,
            pointBorderColor: sampleData.hardness.color,
            pointBorderWidth: 0,
            pointRadius: 3,
            tension: 0.5, // More rounded line
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
                max: 8,
                ticks: {
                    ...commonOptions.scales.y.ticks,
                    stepSize: 1
                }
            }
        }
    }
});

// Custom plugin to draw the pale background bars
const sleepBackgroundPlugin = {
    id: 'sleepBackgroundBars',
    beforeDraw: (chart) => {
        const {ctx, chartArea, scales} = chart;
        const {top, bottom, left, width} = chartArea;
        const barCount = sampleData.dates.length;
        const barWidth = width / barCount * 0.7; // Match the barPercentage
        const barOffset = width / barCount * 0.15; // Center the bars
        
        // Draw pale violet background bars with rounded corners
        ctx.fillStyle = 'rgba(147, 112, 219, 0.2)';
        
        for (let i = 0; i < barCount; i++) {
            const x = left + (width / barCount) * i + barOffset;
            const barHeight = bottom - top;
            
            // Calculate radius - should be half the bar width for pill shape
            const radius = barWidth / 2;
            
            // Draw pill-shaped bar (completely rounded at top)
            ctx.beginPath();
            
            // Draw the top semi-circle
            ctx.arc(x + radius, top + radius, radius, Math.PI, 0, false);
            
            // Draw the sides
            ctx.lineTo(x + barWidth, bottom);
            ctx.lineTo(x, bottom);
            
            // Complete the shape
            ctx.lineTo(x, top + radius);
            
            ctx.closePath();
            ctx.fill();
        }
    }
};

// Custom plugin to draw the actual sleep data bars with rounded corners
const sleepBarsPlugin = {
    id: 'sleepDataBars',
    afterDatasetsDraw: (chart) => {
        const {ctx, chartArea, scales} = chart;
        const {top, bottom, left, width} = chartArea;
        const barCount = sampleData.dates.length;
        const barWidth = width / barCount * 0.7; // Match the barPercentage
        const barOffset = width / barCount * 0.15; // Center the bars
        
        // Get the dataset
        const dataset = chart.data.datasets[0];
        const metaset = chart.getDatasetMeta(0);
        
        // Hide the original bars
        metaset.hidden = true;
        
        // Draw custom rounded bars
        ctx.fillStyle = sampleData.sleep.color;
        
        for (let i = 0; i < dataset.data.length; i++) {
            const value = dataset.data[i];
            const x = left + (width / barCount) * i + barOffset;
            const yTop = scales.y.getPixelForValue(value);
            const barHeight = bottom - yTop;
            
            // Calculate radius - should be half the bar width for pill shape
            const radius = barWidth / 2;
            
            // Draw pill-shaped bar (completely rounded at top)
            ctx.beginPath();
            
            // Draw the top semi-circle
            ctx.arc(x + radius, yTop + radius, radius, Math.PI, 0, false);
            
            // Draw the sides
            ctx.lineTo(x + barWidth, bottom);
            ctx.lineTo(x, bottom);
            
            // Complete the shape
            ctx.lineTo(x, yTop + radius);
            
            ctx.closePath();
            ctx.fill();
        }
    }
};

const sleepCtx = document.getElementById('sleepChart').getContext('2d');
const sleepChart = new Chart(sleepCtx, {
    type: 'bar',
    data: {
        labels: sampleData.dates,
        datasets: [{
            label: 'Сон (години)',
            data: sampleData.sleep.values,
            backgroundColor: sampleData.sleep.color,
            borderColor: 'transparent',
            borderWidth: 0,
            barPercentage: 0.7
        }]
    },
    options: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 7,
                ticks: {
                    ...commonOptions.scales.y.ticks,
                    stepSize: 1
                }
            },
            x: {
                ...commonOptions.scales.x,
                ticks: {
                    ...commonOptions.scales.x.ticks,
                    callback: function(value, index) {
                        // Only show every 4th label to avoid crowding
                        return index % 4 === 0 ? this.getLabelForValue(value) : '';
                    }
                }
            }
        }
    },
    plugins: [sleepBackgroundPlugin, sleepBarsPlugin]
});

// Create feelings chart (line chart)
const feelingsCtx = document.getElementById('feelingsChart').getContext('2d');
const feelingsChart = new Chart(feelingsCtx, {
    type: 'line',
    data: {
        labels: sampleData.dates,
        datasets: [{
            label: 'Самопочуття',
            data: sampleData.feelings.values,
            backgroundColor: 'rgba(0, 255, 0, 0.0)',
            borderColor: sampleData.feelings.color,
            borderWidth: 2,
            pointBackgroundColor: sampleData.feelings.color,
            pointBorderColor: sampleData.feelings.color,
            pointBorderWidth: 0,
            pointRadius: 3,
            tension: 0.5, // More rounded line
            fill: false
        }]
    },
    options: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            x: {
                ...commonOptions.scales.x,
                ticks: {
                    ...commonOptions.scales.x.ticks,
                    callback: function(value, index) {
                        // Only show every 4th label to avoid crowding
                        return index % 4 === 0 ? this.getLabelForValue(value) : '';
                    }
                }
            },
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 8,
                ticks: {
                    ...commonOptions.scales.y.ticks,
                    stepSize: 1
                }
            }
        }
    }
});

// Create weight chart (line chart with gradient)
const weightCtx = document.getElementById('weightChart').getContext('2d');

// Create gradient for weight chart
const weightGradient = weightCtx.createLinearGradient(0, 0, 0, 200);
weightGradient.addColorStop(0, 'rgba(0, 191, 255, 0.7)');
weightGradient.addColorStop(1, 'rgba(0, 191, 255, 0.0)');

const weightChart = new Chart(weightCtx, {
    type: 'line',
    data: {
        labels: sampleData.dates,
        datasets: [{
            label: 'Вага (кг)',
            data: sampleData.weight.values,
            backgroundColor: 'transparent',
            borderColor: sampleData.weight.color,
            borderWidth: 5,
            pointBackgroundColor: 'transparent',
            pointBorderColor: 'transparent',
            pointBorderWidth: 0,
            pointRadius: 0,
            tension: 0.6, // More rounded line
            fill: false
        }]
    },
    options: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            x: {
                ...commonOptions.scales.x,
                ticks: {
                    ...commonOptions.scales.x.ticks,
                    callback: function(value, index) {
                        // Only show every 4th label to avoid crowding
                        return index % 4 === 0 ? this.getLabelForValue(value) : '';
                    }
                }
            },
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 8,
                ticks: {
                    ...commonOptions.scales.y.ticks,
                    stepSize: 1
                }
            }
        }
    }
});

// Add a second dataset for the gradient fill
weightChart.data.datasets.push({
    data: sampleData.weight.values,
    backgroundColor: weightGradient,
    borderColor: 'transparent',
    borderWidth: 0,
    pointRadius: 0,
    fill: true,
    tension: 0.6 // More rounded line
});
weightChart.update();
