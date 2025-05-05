// dashboard.js - Handles the dashboard page functionality

// Declare variables for charts so we can update them
let riskChart = null;
let reflexivityChart = null;
let symbolsData = {};

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Get the currently selected symbol
    const selectedSymbol = document.getElementById('symbol-selector').value;
    
    // Initialize charts
    initializeCharts(selectedSymbol);
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up auto-refresh
    setInterval(function() {
        refreshDashboard();
    }, 60000); // Refresh every minute
});

// Set up event listeners for interactive elements
function setupEventListeners() {
    // Symbol selector change
    document.getElementById('symbol-selector').addEventListener('change', function() {
        const selectedSymbol = this.value;
        initializeCharts(selectedSymbol);
    });
    
    // Time period selector
    document.querySelectorAll('.time-period-selector button').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            document.querySelectorAll('.time-period-selector button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the days value and update charts
            const days = parseInt(this.getAttribute('data-days'));
            const selectedSymbol = document.getElementById('symbol-selector').value;
            updateCharts(selectedSymbol, days);
        });
    });
    
    // Manual refresh button
    document.getElementById('refresh-data').addEventListener('click', function() {
        const selectedSymbol = document.getElementById('symbol-selector').value;
        
        // Show loading spinner
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
        this.disabled = true;
        
        // Call the refresh API
        fetch('/api/data/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol: selectedSymbol })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Refresh the dashboard
                refreshDashboard();
                showToast('Data refreshed successfully', 'success');
            } else {
                showToast('Error refreshing data: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error connecting to server', 'danger');
        })
        .finally(() => {
            // Restore button
            this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Data';
            this.disabled = false;
        });
    });
    
    // Alert acknowledgement
    document.querySelectorAll('.acknowledge-alert').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            acknowledgeAlert(alertId);
        });
    });
}

// Initialize charts with data from the API
function initializeCharts(symbol, days = 30) {
    // Show loading indicators
    document.getElementById('risk-chart-container').innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    document.getElementById('reflexivity-chart-container').innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Fetch data from the API
    fetch(`/api/dashboard/data?symbol=${symbol}&days=${days}`)
        .then(response => response.json())
        .then(data => {
            // Store the data
            symbolsData[symbol] = data;
            
            // Clear loading indicators
            document.getElementById('risk-chart-container').innerHTML = '<canvas id="risk-chart"></canvas>';
            document.getElementById('reflexivity-chart-container').innerHTML = '<canvas id="reflexivity-chart"></canvas>';
            
            // Create charts
            createRiskChart(data);
            createReflexivityChart(data);
            
            // Update market sentiment indicators
            updateMarketSentiment(symbol);
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            document.getElementById('risk-chart-container').innerHTML = '<div class="alert alert-danger">Error loading chart data</div>';
            document.getElementById('reflexivity-chart-container').innerHTML = '<div class="alert alert-danger">Error loading chart data</div>';
        });
}

// Update charts with new time period
function updateCharts(symbol, days) {
    // Fetch data from the API
    fetch(`/api/dashboard/data?symbol=${symbol}&days=${days}`)
        .then(response => response.json())
        .then(data => {
            // Store the data
            symbolsData[symbol] = data;
            
            // Update existing charts
            updateRiskChart(data);
            updateReflexivityChart(data);
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            showToast('Error loading chart data', 'danger');
        });
}

// Create the risk indicators chart
function createRiskChart(data) {
    const ctx = document.getElementById('risk-chart').getContext('2d');
    
    // Get translated labels from the DOM
    const volaxivityLabel = document.querySelector('.risk-level:nth-child(1)').textContent;
    const volatilitySkewLabel = document.querySelector('.risk-level:nth-child(2)').textContent;
    const putCallRatioLabel = document.querySelector('.risk-level:nth-child(3)').textContent;
    
    riskChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps,
            datasets: [
                {
                    label: volaxivityLabel,
                    data: data.volaxivity,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: volatilitySkewLabel,
                    data: data.volatility_skew,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: putCallRatioLabel,
                    data: data.put_call_ratio,
                    borderColor: 'rgba(255, 206, 86, 1)',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                title: {
                    display: true,
                    text: 'Risk Indicators'
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create the reflexivity chart
function createReflexivityChart(data) {
    const ctx = document.getElementById('reflexivity-chart').getContext('2d');
    
    // Get translated labels from the DOM
    const reflexivityLabel = document.querySelector('.risk-level:nth-child(4)').textContent;
    const chartTitle = document.querySelector('.card-header h6').textContent;
    
    reflexivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps,
            datasets: [
                {
                    label: reflexivityLabel,
                    data: data.reflexivity,
                    borderColor: 'rgba(153, 102, 255, 1)',
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                title: {
                    display: true,
                    text: chartTitle
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        callback: function(value) {
                            return (value * 100) + '%';
                        }
                    }
                }
            }
        }
    });
}

// Update the risk chart with new data
function updateRiskChart(data) {
    riskChart.data.labels = data.timestamps;
    riskChart.data.datasets[0].data = data.volaxivity;
    riskChart.data.datasets[1].data = data.volatility_skew;
    riskChart.data.datasets[2].data = data.put_call_ratio;
    riskChart.update();
}

// Update the reflexivity chart with new data
function updateReflexivityChart(data) {
    reflexivityChart.data.labels = data.timestamps;
    reflexivityChart.data.datasets[0].data = data.reflexivity;
    reflexivityChart.update();
}

// Update market sentiment indicators
function updateMarketSentiment(symbol) {
    if (!symbolsData[symbol] || !symbolsData[symbol].timestamps || symbolsData[symbol].timestamps.length === 0) {
        return;
    }
    
    // Get the latest values
    const lastIndex = symbolsData[symbol].timestamps.length - 1;
    const volaxivity = symbolsData[symbol].volaxivity[lastIndex];
    const volatilitySkew = symbolsData[symbol].volatility_skew[lastIndex];
    const putCallRatio = symbolsData[symbol].put_call_ratio[lastIndex];
    const reflexivity = symbolsData[symbol].reflexivity[lastIndex];
    
    // Update the values in the UI
    document.getElementById('volaxivity-value').textContent = volaxivity ? volaxivity.toFixed(2) : 'N/A';
    document.getElementById('volatility-skew-value').textContent = volatilitySkew ? volatilitySkew.toFixed(2) : 'N/A';
    document.getElementById('put-call-ratio-value').textContent = putCallRatio ? putCallRatio.toFixed(2) : 'N/A';
    document.getElementById('reflexivity-value').textContent = reflexivity ? (reflexivity * 100).toFixed(2) + '%' : 'N/A';
    
    // Determine market sentiment (simplified)
    let riskOffSignals = 0;
    
    if (volaxivity > 25) riskOffSignals++;
    if (putCallRatio > 1.2) riskOffSignals++;
    if (reflexivity > 0.5) riskOffSignals++;
    
    const marketSentiment = riskOffSignals >= 2 ? 'risk-off' : 'risk-on';
    
    // Find translations in DOM
    const translatedLabels = {};
    document.querySelectorAll('[data-sentiment]').forEach(el => {
        translatedLabels[el.dataset.sentiment] = el.textContent;
    });
    
    // Get translated sentiment text
    let sentimentText;
    if (marketSentiment === 'risk-on') {
        // Try to find the translation in our DOM, fallback to English
        sentimentText = translatedLabels['risk-on'] || 'Risk-On (Bullish)';
    } else {
        sentimentText = translatedLabels['risk-off'] || 'Risk-Off (Bearish)';
    }
    
    // Update sentiment indicator
    const sentimentElement = document.getElementById('market-sentiment');
    sentimentElement.textContent = sentimentText;
    
    // Update sentiment color
    if (marketSentiment === 'risk-on') {
        sentimentElement.classList.remove('text-danger');
        sentimentElement.classList.add('text-success');
    } else {
        sentimentElement.classList.remove('text-success');
        sentimentElement.classList.add('text-danger');
    }
    
    // Update risk level indicators
    updateRiskLevelIndicator('volaxivity-indicator', volaxivity, [20, 30, 40]);
    updateRiskLevelIndicator('skew-indicator', volatilitySkew, [0.5, 1.0, 1.5]);
    updateRiskLevelIndicator('pcr-indicator', putCallRatio, [1.2, 1.5, 2.0]);
    updateRiskLevelIndicator('reflexivity-indicator', reflexivity, [0.3, 0.5, 0.7]);
}

// Update a risk level indicator based on thresholds
function updateRiskLevelIndicator(elementId, value, thresholds) {
    const indicator = document.getElementById(elementId);
    
    // Remove previous classes
    indicator.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-info');
    
    // Determine risk level
    if (value === null || value === undefined) {
        indicator.classList.add('bg-secondary');
        indicator.style.width = '0%';
    } else if (value < thresholds[0]) {
        indicator.classList.add('bg-success');
        indicator.style.width = (value / thresholds[0] * 25) + '%';
    } else if (value < thresholds[1]) {
        indicator.classList.add('bg-info');
        indicator.style.width = '50%';
    } else if (value < thresholds[2]) {
        indicator.classList.add('bg-warning');
        indicator.style.width = '75%';
    } else {
        indicator.classList.add('bg-danger');
        indicator.style.width = '100%';
    }
}

// Acknowledge an alert
function acknowledgeAlert(alertId) {
    fetch('/api/alerts/acknowledge', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ alert_id: alertId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the alert from the UI
            const alertElement = document.querySelector(`.alert-item[data-alert-id="${alertId}"]`);
            if (alertElement) {
                alertElement.remove();
            }
            
            // Show success message
            showToast('Alert acknowledged', 'success');
        } else {
            showToast('Error acknowledging alert: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error connecting to server', 'danger');
    });
}

// Refresh the dashboard data
function refreshDashboard() {
    const selectedSymbol = document.getElementById('symbol-selector').value;
    const activePeriodButton = document.querySelector('.time-period-selector button.active');
    const days = activePeriodButton ? parseInt(activePeriodButton.getAttribute('data-days')) : 7;
    
    updateCharts(selectedSymbol, days);
    
    // Reload alerts section
    fetch('/alerts')
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Get the alerts container from the loaded HTML
            const newAlertsContainer = doc.querySelector('#active-alerts');
            
            if (newAlertsContainer) {
                // Replace the current alerts container
                document.getElementById('active-alerts').innerHTML = newAlertsContainer.innerHTML;
                
                // Reattach event listeners
                document.querySelectorAll('.acknowledge-alert').forEach(button => {
                    button.addEventListener('click', function() {
                        const alertId = this.getAttribute('data-alert-id');
                        acknowledgeAlert(alertId);
                    });
                });
            }
        })
        .catch(error => {
            console.error('Error refreshing alerts:', error);
        });
}

// Show a toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    bsToast.show();
    
    // Remove the toast from the DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toastContainer.removeChild(toast);
    });
}
