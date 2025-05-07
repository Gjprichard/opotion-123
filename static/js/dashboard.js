// dashboard.js - 完全重构的仪表盘功能
// 用于显示期权市场风险监控数据

// 声明全局变量以存储图表对象
let riskChart = null;
let reflexivityChart = null;
let symbolsData = {};

// 当页面加载完成时初始化仪表盘
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化仪表盘...');
    console.log('检查Chart.js是否加载:', typeof Chart !== 'undefined' ? '已加载' : '未加载');
    
    if (typeof Chart === 'undefined') {
        console.error('Chart.js未加载，这会导致图表创建失败');
        showToast('图表库未加载，请刷新页面或检查网络连接', 'danger');
        return;
    }

    // 确保全局图表对象存在
    if (!window.chartObjects) {
        window.chartObjects = {};
        console.log('初始化全局图表对象容器');
    }

    try {
        // 初始化事件监听器
        setupEventListeners();
        console.log('事件监听器设置完成');
        
        // 获取当前选择的交易对和时间周期
        const symbolSelector = document.getElementById('symbol-selector');
        const timePeriodSelector = document.getElementById('time-period-selector');
        
        if (!symbolSelector) {
            console.warn('警告: 找不到交易对选择器 #symbol-selector');
        }
        
        if (!timePeriodSelector) {
            console.warn('警告: 找不到时间周期选择器 #time-period-selector');
        }
        
        const selectedSymbol = symbolSelector?.value || 'BTC';
        const selectedTimePeriod = timePeriodSelector?.value || '15m';
        
        console.log('初始选择:', {selectedSymbol, selectedTimePeriod});

        // 初始化图表
        console.log('开始初始化图表数据');
        loadDashboardData(selectedSymbol, 30, selectedTimePeriod);

        // 设置自动刷新（每10分钟）与后端计算频率一致
        console.log('设置自动刷新定时器，间隔10分钟');
        const refreshInterval = setInterval(function() {
            const currentSymbol = document.getElementById('symbol-selector')?.value || 'BTC';
            const currentTimePeriod = document.getElementById('time-period-selector')?.value || '15m';
            console.log('自动刷新图表数据:', {currentSymbol, currentTimePeriod});
            loadDashboardData(currentSymbol, 30, currentTimePeriod);
        }, 600000); // 10 minutes (600000ms)
        
        // 在页面上显示初始化完成信息
        showToast('仪表盘初始化完成，正在加载数据...', 'info');
    } catch (error) {
        console.error('仪表盘初始化出错:', error);
        showToast('仪表盘初始化出错: ' + error.message, 'danger');
    }
});

// 设置所有事件监听器
function setupEventListeners() {
    console.log('设置事件监听器...');

    // 交易对选择器变化时更新数据
    const symbolSelector = document.getElementById('symbol-selector');
    if (symbolSelector) {
        symbolSelector.addEventListener('change', function() {
            const symbol = this.value;
            const timePeriod = document.getElementById('time-period-selector').value || '15m';
            loadDashboardData(symbol, 30, timePeriod);
        });
    }

    // 时间周期选择器变化时更新数据
    const timePeriodSelector = document.getElementById('time-period-selector');
    if (timePeriodSelector) {
        timePeriodSelector.addEventListener('change', function() {
            const symbol = document.getElementById('symbol-selector').value || 'BTC';
            const timePeriod = this.value;
            loadDashboardData(symbol, 30, timePeriod);
        });
    }

    // 历史图表的时间周期按钮
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
                const timePeriod = document.getElementById('time-period-selector').value || '15m';
                loadDashboardData(symbol, days, timePeriod);
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
            const timePeriod = document.getElementById('time-period-selector').value || '15m';

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
                    loadDashboardData(symbol, 30, timePeriod);
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
function loadDashboardData(symbol, days = 30, timePeriod = '15m') {
    console.log(`加载${symbol}的最近${days}天数据，时间周期：${timePeriod}...`);

    // 初始化全局图表对象容器
    if (!window.chartObjects) {
        window.chartObjects = {};
        console.log('初始化全局图表对象容器');
    }

    // 获取图表容器
    const riskChartContainer = document.getElementById('risk-chart-container');
    const reflexivityChartContainer = document.getElementById('reflexivity-chart-container');
    
    // 检查DOM元素是否存在
    if (!riskChartContainer) {
        console.error('错误: 找不到风险图表容器元素 #risk-chart-container');
    }
    
    if (!reflexivityChartContainer) {
        console.error('错误: 找不到反身性图表容器元素 #reflexivity-chart-container');
    }
    
    // 仅在首次加载或没有有效图表时显示加载指示器
    if (riskChartContainer && (!window.chartObjects.riskChart)) {
        console.log('显示风险图表加载指示器');
        riskChartContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }

    if (reflexivityChartContainer && (!window.chartObjects.reflexivityChart)) {
        console.log('显示反身性图表加载指示器');
        reflexivityChartContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }

    // 显示刷新状态 - 仅在页面顶部提示，不干扰图表
    const lastUpdateElement = document.getElementById('last-update-time');
    if (lastUpdateElement) {
        lastUpdateElement.innerHTML = '<small><i class="fas fa-sync-alt fa-spin"></i> 正在获取数据...</small>';
    } else {
        console.warn('警告: 找不到最后更新时间元素 #last-update-time');
    }

    // 调用API获取数据，包含时间周期
    const apiUrl = `/api/dashboard/data?symbol=${symbol}&days=${days}&time_period=${timePeriod}`;
    console.log('API请求URL:', apiUrl);
    
    fetch(apiUrl)
        .then(response => {
            console.log('API响应状态:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('获取到的数据:', data);
            
            // 检查数据是否有效
            if (!data || (!data.timestamps || data.timestamps.length === 0)) {
                console.error('接收到无效数据结构:', data);
                throw new Error('接收到的数据无效，缺少必要的数据点');
            }

            // 存储数据以供后续使用
            symbolsData[symbol] = data;

            // 仅在没有有效图表时重建容器
            if (riskChartContainer && (!window.chartObjects.riskChart)) {
                console.log('重建风险图表容器');
                riskChartContainer.innerHTML = '<canvas id="risk-chart"></canvas>';
            }

            if (reflexivityChartContainer && (!window.chartObjects.reflexivityChart)) {
                console.log('重建反身性图表容器');
                reflexivityChartContainer.innerHTML = '<canvas id="reflexivity-chart"></canvas>';
            }

            // 检查图表DOM元素
            const riskChartEl = document.getElementById('risk-chart');
            const reflexivityChartEl = document.getElementById('reflexivity-chart');
            
            if (!riskChartEl) console.error('错误: 找不到风险图表元素 #risk-chart');
            if (!reflexivityChartEl) console.error('错误: 找不到反身性图表元素 #reflexivity-chart');

            // 创建或更新图表
            try {
                createRiskChart(data);
                console.log('风险图表创建完成');
            } catch (e) {
                console.error('创建风险图表出错:', e);
            }
            
            try {
                createReflexivityChart(data);
                console.log('反身性图表创建完成');
            } catch (e) {
                console.error('创建反身性图表出错:', e);
            }

            // 更新市场情绪和风险指标显示
            try {
                updateRiskIndicators(symbol, data);
                console.log('风险指标更新完成');
            } catch (e) {
                console.error('更新风险指标出错:', e);
            }
            
            // 更新最后刷新时间
            if (lastUpdateElement) {
                const now = new Date();
                const timeString = now.toLocaleTimeString();
                lastUpdateElement.innerHTML = `<small>最后更新: ${timeString}</small>`;
            }
        })
        .catch(error => {
            console.error('获取仪表盘数据出错:', error);

            // 保留现有图表，仅显示错误信息提示
            if (lastUpdateElement) {
                lastUpdateElement.innerHTML = '<small class="text-danger"><i class="fas fa-exclamation-triangle"></i> 数据获取失败</small>';
            }
            
            // 只有在没有图表的情况下才显示错误提示替代图表
            if (riskChartContainer && (!window.chartObjects.riskChart)) {
                riskChartContainer.innerHTML = '<div class="alert alert-danger">加载图表数据出错: ' + error.message + '</div>';
            }

            if (reflexivityChartContainer && (!window.chartObjects.reflexivityChart)) {
                reflexivityChartContainer.innerHTML = '<div class="alert alert-danger">加载图表数据出错: ' + error.message + '</div>';
            }
            
            // 显示错误通知
            showToast('获取数据失败: ' + error.message + '，将在下次自动刷新时重试', 'warning');
            
            // 尝试显示额外的调试信息
            console.log('调试信息 - 环境检查:');
            console.log('Chart.js 是否加载:', typeof Chart !== 'undefined' ? '是' : '否');
            console.log('符号数据对象:', symbolsData);
            console.log('DOM元素检查:');
            console.log('- risk-chart-container:', riskChartContainer ? '存在' : '不存在');
            console.log('- reflexivity-chart-container:', reflexivityChartContainer ? '存在' : '不存在');
            console.log('- risk-chart:', document.getElementById('risk-chart') ? '存在' : '不存在');
            console.log('- reflexivity-chart:', document.getElementById('reflexivity-chart') ? '存在' : '不存在');
        });
}

// 创建风险指标图表
function createRiskChart(data) {
    console.log('创建风险指标图表...');
    
    // 检查数据有效性
    if (!data || !data.timestamps || data.timestamps.length === 0) {
        console.error('创建风险图表失败：无效的数据格式', data);
        showToast('无法显示风险图表：数据格式无效', 'danger');
        return;
    }

    const riskChartElement = document.getElementById('risk-chart');
    if (!riskChartElement) {
        console.error('找不到风险图表元素 #risk-chart');
        return;
    }

    try {
        const ctx = riskChartElement.getContext('2d');
        if (!ctx) {
            console.error('无法获取图表上下文');
            return;
        }

        // 获取翻译后的标签
        const volaxivityLabel = document.querySelector('.risk-level:nth-child(1)')?.textContent || 'Volaxivity';
        const volatilitySkewLabel = document.querySelector('.risk-level:nth-child(2)')?.textContent || 'Volatility Skew';
        const putCallRatioLabel = document.querySelector('.risk-level:nth-child(3)')?.textContent || 'Put/Call Ratio';

        console.log('使用的标签:', {volaxivityLabel, volatilitySkewLabel, putCallRatioLabel});
        console.log('图表数据长度:', {
            timestamps: data.timestamps?.length || 0,
            volaxivity: data.volaxivity?.length || 0,
            volatility_skew: data.volatility_skew?.length || 0,
            put_call_ratio: data.put_call_ratio?.length || 0
        });

        // 销毁现有图表（如果存在）
        if (riskChart) {
            console.log('销毁现有风险图表');
            riskChart.destroy();
        } else {
            console.log('没有现有风险图表需要销毁');
        }

        // 确保全局图表对象存在
        if (!window.chartObjects) {
            window.chartObjects = {};
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

        // 将图表保存到全局对象中
        window.chartObjects.riskChart = riskChart;
        console.log('风险图表创建成功');
    } catch (error) {
        console.error('创建风险图表时出错:', error);
        showToast('创建风险图表时出错: ' + error.message, 'danger');
    }
}

// 创建反身性指标图表
function createReflexivityChart(data) {
    console.log('创建反身性指标图表...');
    
    // 检查数据有效性
    if (!data || !data.timestamps || data.timestamps.length === 0) {
        console.error('创建反身性图表失败：无效的数据格式', data);
        showToast('无法显示反身性图表：数据格式无效', 'danger');
        return;
    }

    const reflexivityChartElement = document.getElementById('reflexivity-chart');
    if (!reflexivityChartElement) {
        console.error('找不到反身性图表元素 #reflexivity-chart');
        return;
    }

    try {
        const ctx = reflexivityChartElement.getContext('2d');
        if (!ctx) {
            console.error('无法获取反身性图表上下文');
            return;
        }

        // 获取翻译后的标签
        const reflexivityLabel = document.querySelector('.risk-level:nth-child(4)')?.textContent || 'Reflexivity Indicator';
        
        console.log('反身性标签:', reflexivityLabel);
        console.log('反身性数据长度:', {
            timestamps: data.timestamps?.length || 0,
            reflexivity_indicator: data.reflexivity_indicator?.length || 0
        });

        // 销毁现有图表（如果存在）
        if (reflexivityChart) {
            console.log('销毁现有反身性图表');
            reflexivityChart.destroy();
        } else {
            console.log('没有现有反身性图表需要销毁');
        }

        // 确保全局图表对象存在
        if (!window.chartObjects) {
            window.chartObjects = {};
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
                                if (context.raw === null || context.raw === undefined) {
                                    return context.dataset.label + ': N/A';
                                }
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

        // 将图表保存到全局对象中
        window.chartObjects.reflexivityChart = reflexivityChart;
        console.log('反身性图表创建成功');
    } catch (error) {
        console.error('创建反身性图表时出错:', error);
        showToast('创建反身性图表时出错: ' + error.message, 'danger');
    }
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

    // 确定市场情绪（根据选择的时间周期设置不同的阈值）
    let riskOffSignals = 0;
    let timePeriod = document.getElementById('time-period-selector').value || '15m';

    // 根据时间周期设置不同的阈值
    let volaxivityThreshold, pcrThreshold, reflexivityThreshold;

    switch(timePeriod) {
        case '15m':
            volaxivityThreshold = 20;
            pcrThreshold = 1.1;
            reflexivityThreshold = 0.3;
            break;
        case '1h':
            volaxivityThreshold = 22;
            pcrThreshold = 1.15;
            reflexivityThreshold = 0.35;
            break;
        case '4h':
            volaxivityThreshold = 25;
            pcrThreshold = 1.2;
            reflexivityThreshold = 0.5;
            break;
        case '1d':
            volaxivityThreshold = 28;
            pcrThreshold = 1.25;
            reflexivityThreshold = 0.6;
            break;
        case '7d':
            volaxivityThreshold = 32;
            pcrThreshold = 1.3;
            reflexivityThreshold = 0.7;
            break;
        case '30d':
            volaxivityThreshold = 35;
            pcrThreshold = 1.35;
            reflexivityThreshold = 0.8;
            break;
        default:
            volaxivityThreshold = 25;
            pcrThreshold = 1.2;
            reflexivityThreshold = 0.5;
    }

    if (volaxivity > volaxivityThreshold) riskOffSignals++;
    if (putCallRatio > pcrThreshold) riskOffSignals++;
    if (reflexivity > reflexivityThreshold) riskOffSignals++;

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

    // 更新风险等级指示器 - 根据时间周期设置不同的阈值
    let volaxivityLevels, skewLevels, pcrLevels, reflexivityLevels;

    // 根据时间周期设置不同的风险等级阈值
    switch(timePeriod) {
        case '15m':
            volaxivityLevels = [15, 25, 35];
            skewLevels = [0.3, 0.7, 1.2];
            pcrLevels = [1.1, 1.4, 1.8];
            reflexivityLevels = [0.2, 0.4, 0.6];
            break;
        case '1h':
            volaxivityLevels = [18, 28, 38];
            skewLevels = [0.4, 0.8, 1.3];
            pcrLevels = [1.15, 1.45, 1.9];
            reflexivityLevels = [0.25, 0.45, 0.65];
            break;
        case '4h':
            volaxivityLevels = [20, 30, 40];
            skewLevels = [0.5, 1.0, 1.5];
            pcrLevels = [1.2, 1.5, 2.0];
            reflexivityLevels = [0.3, 0.5, 0.7];
            break;
        case '1d':
            volaxivityLevels = [22, 32, 42];
            skewLevels = [0.6, 1.1, 1.6];
            pcrLevels = [1.25, 1.55, 2.1];
            reflexivityLevels = [0.35, 0.55, 0.75];
            break;
        case '7d':
            volaxivityLevels = [25, 35, 45];
            skewLevels = [0.7, 1.2, 1.7];
            pcrLevels = [1.3, 1.6, 2.2];
            reflexivityLevels = [0.4, 0.6, 0.8];
            break;
        case '30d':
            volaxivityLevels = [30, 40, 50];
            skewLevels = [0.8, 1.3, 1.8];
            pcrLevels = [1.35, 1.7, 2.3];
            reflexivityLevels = [0.45, 0.65, 0.85];
            break;
        default:
            volaxivityLevels = [20, 30, 40];
            skewLevels = [0.5, 1.0, 1.5];
            pcrLevels = [1.2, 1.5, 2.0];
            reflexivityLevels = [0.3, 0.5, 0.7];
    }

    updateRiskLevelIndicator('volaxivity-indicator', volaxivity, volaxivityLevels);
    updateRiskLevelIndicator('skew-indicator', volatilitySkew, skewLevels);
    updateRiskLevelIndicator('pcr-indicator', putCallRatio, pcrLevels);
    updateRiskLevelIndicator('reflexivity-indicator', reflexivity, reflexivityLevels);
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