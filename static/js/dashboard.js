// dashboard.js - 完全重构的仪表盘功能
// 用于显示期权市场风险监控数据

// 声明全局变量以存储图表对象
let riskChart = null;
let reflexivityChart = null;
let symbolsData = {};

// 当页面加载完成时初始化仪表盘
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化仪表盘...');
    
    // 初始化事件监听器
    setupEventListeners();
    
    // 获取当前选择的交易对
    const selectedSymbol = document.getElementById('symbol-selector').value || 'BTC';
    
    // 初始化图表
    loadDashboardData(selectedSymbol, 30);
    
    // 设置自动刷新（每分钟）
    setInterval(function() {
        const currentSymbol = document.getElementById('symbol-selector').value || 'BTC';
        loadDashboardData(currentSymbol, 30);
    }, 60000);
});

// 设置所有事件监听器
function setupEventListeners() {
    console.log('设置事件监听器...');
    
    // 交易对选择器变化时更新数据
    const symbolSelector = document.getElementById('symbol-selector');
    if (symbolSelector) {
        symbolSelector.addEventListener('change', function() {
            const symbol = this.value;
            loadDashboardData(symbol, 30);
        });
    }
    
    // 时间周期选择器
    const timeButtons = document.querySelectorAll('.time-period-selector button');
    if (timeButtons.length > 0) {
        timeButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 移除所有按钮的active类
                timeButtons.forEach(btn => btn.classList.remove('active'));
                
                // 添加active类到当前按钮
                this.classList.add('active');
                
                // 获取天数和符号并更新图表
                const days = parseInt(this.getAttribute('data-days')) || 30;
                const symbol = document.getElementById('symbol-selector').value || 'BTC';
                loadDashboardData(symbol, days);
            });
        });
    }
    
    // 刷新数据按钮
    const refreshButton = document.getElementById('refresh-data');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // 显示加载状态
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 刷新中...';
            this.disabled = true;
            
            const symbol = document.getElementById('symbol-selector').value || 'BTC';
            
            // 调用API刷新数据
            fetch('/api/data/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ symbol: symbol })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 刷新成功后重新加载仪表盘数据
                    loadDashboardData(symbol, 30);
                    showToast('数据刷新成功', 'success');
                } else {
                    showToast('刷新数据失败: ' + (data.message || '未知错误'), 'danger');
                }
            })
            .catch(error => {
                console.error('刷新数据出错:', error);
                showToast('连接服务器出错', 'danger');
            })
            .finally(() => {
                // 恢复按钮状态
                refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i> 刷新数据';
                refreshButton.disabled = false;
            });
        });
    }
    
    // 警报确认按钮
    document.querySelectorAll('.acknowledge-alert').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            acknowledgeAlert(alertId);
        });
    });
}

// 加载仪表盘数据
function loadDashboardData(symbol, days = 30) {
    console.log(`加载${symbol}的最近${days}天数据...`);
    
    // 显示加载指示器
    const riskChartContainer = document.getElementById('risk-chart-container');
    const reflexivityChartContainer = document.getElementById('reflexivity-chart-container');
    
    if (riskChartContainer) {
        riskChartContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }
    
    if (reflexivityChartContainer) {
        reflexivityChartContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }
    
    // 调用API获取数据
    fetch(`/api/dashboard/data?symbol=${symbol}&days=${days}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('获取到的数据:', data);
            
            // 存储数据以供后续使用
            symbolsData[symbol] = data;
            
            // 清除加载指示器
            if (riskChartContainer) {
                riskChartContainer.innerHTML = '<canvas id="risk-chart"></canvas>';
            }
            
            if (reflexivityChartContainer) {
                reflexivityChartContainer.innerHTML = '<canvas id="reflexivity-chart"></canvas>';
            }
            
            // 创建图表
            createRiskChart(data);
            createReflexivityChart(data);
            
            // 更新市场情绪和风险指标显示
            updateRiskIndicators(symbol, data);
        })
        .catch(error => {
            console.error('获取仪表盘数据出错:', error);
            
            if (riskChartContainer) {
                riskChartContainer.innerHTML = '<div class="alert alert-danger">加载图表数据出错</div>';
            }
            
            if (reflexivityChartContainer) {
                reflexivityChartContainer.innerHTML = '<div class="alert alert-danger">加载图表数据出错</div>';
            }
        });
}

// 创建风险指标图表
function createRiskChart(data) {
    console.log('创建风险指标图表...');
    
    const riskChartElement = document.getElementById('risk-chart');
    if (!riskChartElement) return;
    
    const ctx = riskChartElement.getContext('2d');
    
    // 获取翻译后的标签
    const volaxivityLabel = document.querySelector('.risk-level:nth-child(1)')?.textContent || 'Volaxivity';
    const volatilitySkewLabel = document.querySelector('.risk-level:nth-child(2)')?.textContent || 'Volatility Skew';
    const putCallRatioLabel = document.querySelector('.risk-level:nth-child(3)')?.textContent || 'Put/Call Ratio';
    
    // 销毁现有图表（如果存在）
    if (riskChart) {
        riskChart.destroy();
    }
    
    // 创建新图表
    riskChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps || [],
            datasets: [
                {
                    label: volaxivityLabel,
                    data: data.volaxivity || [],
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: volatilitySkewLabel,
                    data: data.volatility_skew || [],
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: putCallRatioLabel,
                    data: data.put_call_ratio || [],
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
                    text: '风险指标'
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

// 创建反身性指标图表
function createReflexivityChart(data) {
    console.log('创建反身性指标图表...');
    
    const reflexivityChartElement = document.getElementById('reflexivity-chart');
    if (!reflexivityChartElement) return;
    
    const ctx = reflexivityChartElement.getContext('2d');
    
    // 获取翻译后的标签
    const reflexivityLabel = document.querySelector('.risk-level:nth-child(4)')?.textContent || 'Reflexivity Indicator';
    
    // 销毁现有图表（如果存在）
    if (reflexivityChart) {
        reflexivityChart.destroy();
    }
    
    // 创建新图表
    reflexivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.timestamps || [],
            datasets: [
                {
                    label: reflexivityLabel,
                    data: data.reflexivity_indicator || [],
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
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + (context.raw * 100).toFixed(2) + '%';
                        }
                    }
                },
                title: {
                    display: true,
                    text: '反身性指标'
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
                            return (value * 100).toFixed(0) + '%';
                        }
                    }
                }
            }
        }
    });
}

// 更新风险指标和市场情绪显示
function updateRiskIndicators(symbol, data) {
    console.log('更新风险指标显示...');
    
    if (!data || !data.timestamps || data.timestamps.length === 0) {
        console.warn('没有可用数据来更新风险指标');
        return;
    }
    
    // 获取最新的数据点
    const lastIndex = data.timestamps.length - 1;
    const volaxivity = data.volaxivity ? data.volaxivity[lastIndex] : null;
    const volatilitySkew = data.volatility_skew ? data.volatility_skew[lastIndex] : null;
    const putCallRatio = data.put_call_ratio ? data.put_call_ratio[lastIndex] : null;
    const reflexivity = data.reflexivity_indicator ? data.reflexivity_indicator[lastIndex] : null;
    
    // 更新UI中的值
    updateElementText('volaxivity-value', volaxivity ? volaxivity.toFixed(2) : 'N/A');
    updateElementText('volatility-skew-value', volatilitySkew ? volatilitySkew.toFixed(2) : 'N/A');
    updateElementText('put-call-ratio-value', putCallRatio ? putCallRatio.toFixed(2) : 'N/A');
    updateElementText('reflexivity-value', reflexivity ? (reflexivity * 100).toFixed(2) + '%' : 'N/A');
    
    // 确定市场情绪（简化版本）
    let riskOffSignals = 0;
    
    if (volaxivity > 25) riskOffSignals++;
    if (putCallRatio > 1.2) riskOffSignals++;
    if (reflexivity > 0.5) riskOffSignals++;
    
    const marketSentiment = riskOffSignals >= 2 ? 'risk-off' : 'risk-on';
    
    // 查找翻译标签
    const riskOnText = document.querySelector('[data-sentiment="risk-on"]')?.textContent || 'Risk-On (Bullish)';
    const riskOffText = document.querySelector('[data-sentiment="risk-off"]')?.textContent || 'Risk-Off (Bearish)';
    
    // 更新市场情绪文本
    const sentimentText = marketSentiment === 'risk-on' ? riskOnText : riskOffText;
    updateElementText('market-sentiment', sentimentText);
    
    // 更新情绪颜色
    const sentimentElement = document.getElementById('market-sentiment');
    if (sentimentElement) {
        if (marketSentiment === 'risk-on') {
            sentimentElement.classList.remove('text-danger');
            sentimentElement.classList.add('text-success');
        } else {
            sentimentElement.classList.remove('text-success');
            sentimentElement.classList.add('text-danger');
        }
    }
    
    // 更新风险等级指示器
    updateRiskLevelIndicator('volaxivity-indicator', volaxivity, [20, 30, 40]);
    updateRiskLevelIndicator('skew-indicator', volatilitySkew, [0.5, 1.0, 1.5]);
    updateRiskLevelIndicator('pcr-indicator', putCallRatio, [1.2, 1.5, 2.0]);
    updateRiskLevelIndicator('reflexivity-indicator', reflexivity, [0.3, 0.5, 0.7]);
}

// 更新元素文本内容的辅助函数
function updateElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

// 根据阈值更新风险等级指示器
function updateRiskLevelIndicator(elementId, value, thresholds) {
    const indicator = document.getElementById(elementId);
    if (!indicator) return;
    
    // 移除之前的类
    indicator.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-info', 'bg-secondary');
    
    // 确定风险等级
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

// 确认警报
function acknowledgeAlert(alertId) {
    console.log('确认警报:', alertId);
    
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
            // 从UI中移除警报元素
            const alertElement = document.querySelector(`.alert-item[data-alert-id="${alertId}"]`);
            if (alertElement) {
                alertElement.remove();
            }
            
            // 显示成功消息
            showToast('警报已确认', 'success');
        } else {
            showToast('确认警报失败: ' + (data.message || '未知错误'), 'danger');
        }
    })
    .catch(error => {
        console.error('确认警报出错:', error);
        showToast('连接服务器出错', 'danger');
    });
}

// 显示弹出消息
function showToast(message, type = 'info') {
    console.log(`显示消息 [${type}]:`, message);
    
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.warn('找不到Toast容器元素');
        return;
    }
    
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
    
    // 使用Bootstrap的Toast组件
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    bsToast.show();
    
    // 隐藏后从DOM中移除
    toast.addEventListener('hidden.bs.toast', function() {
        toastContainer.removeChild(toast);
    });
}