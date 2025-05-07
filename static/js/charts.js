// charts.js - Shared chart utilities and configuration

// Set default Chart.js options
Chart.defaults.color = '#dee2e6';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';

// Function to create a line chart
function createLineChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default options for line charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            x: {
                ticks: {
                    maxTicksLimit: 10
                }
            },
            y: {
                beginAtZero: options.beginAtZero !== undefined ? options.beginAtZero : true
            }
        }
    };
    
    // Merge options
    const chartOptions = {...defaultOptions, ...options};
    
    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: chartOptions
    });
}

// Function to create a bar chart
function createBarChart(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default options for bar charts
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    };
    
    // Merge options
    const chartOptions = {...defaultOptions, ...options};
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: chartOptions
    });
}

// Function to create a heatmap (using Chart.js matrix controller plugin)
function createHeatmap(elementId, data, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default options for heatmaps
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return `Value: ${context.raw.v}`;
                    }
                }
            }
        },
        scales: {
            x: {
                type: 'category',
                labels: data.xLabels,
                ticks: {
                    display: true
                }
            },
            y: {
                type: 'category',
                labels: data.yLabels,
                ticks: {
                    display: true
                }
            }
        }
    };
    
    // Merge options
    const chartOptions = {...defaultOptions, ...options};
    
    const chartData = {
        datasets: [{
            label: options.title || 'Heatmap',
            data: data.values,
            backgroundColor: function(context) {
                const value = context.dataset.data[context.dataIndex].v;
                const min = data.min || 0;
                const max = data.max || 1;
                const normalized = (value - min) / (max - min);
                
                // Color scale from green to red
                const red = Math.round(normalized * 255);
                const green = Math.round((1 - normalized) * 255);
                return `rgba(${red}, ${green}, 0, 0.8)`;
            },
            borderWidth: 1,
            borderColor: 'rgba(0, 0, 0, 0.2)',
            width: ({ chart }) => (chart.chartArea || {}).width / data.xLabels.length - 1,
            height: ({ chart }) => (chart.chartArea || {}).height / data.yLabels.length - 1
        }]
    };
    
    return new Chart(ctx, {
        type: 'matrix',
        data: chartData,
        options: chartOptions
    });
}

// Function to create a volatility surface chart (3D chart using Chart.js Scatter GL plugin)
function createVolatilitySurface(elementId, data, options = {}) {
    // If 3D visualization is needed, we'd implement it here
    // For now, we'll create a 2D representation using a scatter plot
    
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default options
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return `Strike: ${context.raw.x}, Expiry: ${context.raw.y}, IV: ${context.raw.z.toFixed(2)}`;
                    }
                }
            }
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Strike Price'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Days to Expiration'
                }
            }
        }
    };
    
    // Merge options
    const chartOptions = {...defaultOptions, ...options};
    
    // Convert data points for scatter plot
    // data should be an array of {strike, expiry, iv} objects
    const chartData = {
        datasets: [{
            label: 'Implied Volatility Surface',
            data: data.map(point => ({
                x: point.strike,
                y: point.expiry,
                z: point.iv
            })),
            backgroundColor: function(context) {
                const value = context.raw.z;
                const min = options.min || 0.1;
                const max = options.max || 0.5;
                const normalized = (value - min) / (max - min);
                
                // Color scale from blue to red
                const red = Math.round(normalized * 255);
                const blue = Math.round((1 - normalized) * 255);
                return `rgba(${red}, 100, ${blue}, 0.8)`;
            },
            pointRadius: 5
        }]
    };
    
    return new Chart(ctx, {
        type: 'scatter',
        data: chartData,
        options: chartOptions
    });
}

// Function to create a gauge chart for risk indicators
function createGaugeChart(elementId, value, options = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default thresholds
    const thresholds = options.thresholds || [0.3, 0.7, 1.0];
    
    // Calculate the angle based on the value (0 to 1)
    const normalizedValue = Math.min(1, Math.max(0, value / thresholds[2]));
    const angle = normalizedValue * Math.PI;
    
    // Colors for different zones
    const colors = [
        'rgba(40, 167, 69, 0.8)',  // Green (low risk)
        'rgba(255, 193, 7, 0.8)',  // Yellow (medium risk)
        'rgba(220, 53, 69, 0.8)'   // Red (high risk)
    ];
    
    // Determine the color based on thresholds
    let color;
    if (value < thresholds[0]) {
        color = colors[0];
    } else if (value < thresholds[1]) {
        color = colors[1];
    } else {
        color = colors[2];
    }
    
    // Create the chart
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [value, thresholds[2] - value],
                backgroundColor: [color, 'rgba(0, 0, 0, 0.1)'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: Math.PI,
            rotation: Math.PI,
            cutout: '75%',
            plugins: {
                tooltip: {
                    enabled: false
                },
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: options.title || 'Risk Level',
                    position: 'bottom'
                }
            }
        },
        plugins: [{
            id: 'gaugeNeedle',
            afterDatasetDraw(chart) {
                const {ctx, data, chartArea} = chart;
                ctx.save();
                
                // Draw the value text
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = 'bold 24px Arial';
                ctx.fillStyle = color;
                ctx.fillText(
                    value.toFixed(2), 
                    chartArea.left + chartArea.width / 2, 
                    chartArea.top + chartArea.height * 0.7
                );
                
                ctx.restore();
            }
        }]
    });
}
