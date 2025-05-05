// deviation_monitor.js - 期权执行价偏离监控功能
// 用于监控BTC/ETH期权中执行价偏离当前市场价的合约

// 全局变量
let deviationData = [];
let deviationChart = null;
let pcrComparisonChart = null;
let volumeDistributionChart = null;
let premiumSpreadChart = null;

// 当页面加载完成时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化偏离监控...');
    
    // 初始化事件监听器
    setupEventListeners();
    
    // 添加测试输出提示
    console.log('初始化偏离监控成功，版本: 2025.05.05.001');
    
    // 获取初始数据
    fetchDeviationData();
    fetchRiskData();
});

// 设置事件监听器
function setupEventListeners() {
    // 筛选应用按钮
    document.getElementById('apply-filters-btn').addEventListener('click', applyFilters);
    
    // 刷新数据按钮
    document.getElementById('refresh-data-btn').addEventListener('click', refreshData);
    
    // 导出CSV按钮
    document.getElementById('export-csv').addEventListener('click', exportCsv);
    
    // 警报确认按钮
    document.querySelectorAll('.acknowledge-alert').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            acknowledgeAlert(alertId);
        });
    });
}

// 应用筛选器
function applyFilters() {
    const symbol = document.getElementById('symbol-filter').value;
    const exchange = document.getElementById('exchange-filter').value;
    const optionType = document.getElementById('option-type-filter').value;
    const timePeriod = document.getElementById('time-period-filter').value;
    const days = document.getElementById('days-filter').value;
    const volumeChangeFilter = document.getElementById('volume-change-filter').value;
    const anomalyOnly = document.getElementById('anomaly-only-filter').checked;
    
    console.log('应用筛选: ', {
        symbol, 
        exchange, 
        optionType, 
        timePeriod, 
        days, 
        volumeChangeFilter, 
        anomalyOnly
    });
    
    // 在修改URL历史记录的同时获取数据（不重载页面）
    let params = new URLSearchParams({
        symbol: symbol,
        exchange: exchange,
        time_period: timePeriod,
        days: days,
        anomaly_only: anomalyOnly,
        volume_change_filter: volumeChangeFilter
    });
    
    // 仅当选择了特定期权类型时添加参数
    if (optionType) {
        params.append('option_type', optionType);
    }
    
    // 使用 history.pushState 更新 URL，但不重载页面
    const newUrl = `/deviation-monitor?${params.toString()}`;
    window.history.pushState({ path: newUrl }, '', newUrl);
    
    // 直接获取数据，不重载页面
    fetchDeviationData(true);
    // 同时更新风险指标
    fetchRiskData();
}

// 刷新数据
function refreshData() {
    // 显示刷新按钮上的加载动画
    const refreshBtn = document.getElementById('refresh-data-btn');
    const originalText = refreshBtn.innerHTML;
    refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
    refreshBtn.disabled = true;
    
    // 获取新数据
    Promise.all([
        fetchDeviationData(true),
        fetchRiskData()
    ]).finally(() => {
        // 恢复按钮状态
        refreshBtn.innerHTML = originalText;
        refreshBtn.disabled = false;
    });
}

// 获取风险数据
async function fetchRiskData() {
    const symbol = document.getElementById('symbol-filter').value;
    const timePeriod = document.getElementById('time-period-filter').value;
    
    try {
        const response = await fetch(`/api/dashboard/data?symbol=${symbol}&days=30&time_period=${timePeriod}`);
        const data = await response.json();
        
        if (response.ok) {
            // 更新风险指标值
            updateRiskIndicators(symbol, data, timePeriod);
        } else {
            console.error('Error fetching risk data:', data.message);
        }
    } catch (error) {
        console.error('Fetch error for risk data:', error);
    }
}

// 更新风险指标
function updateRiskIndicators(symbol, data, timePeriod) {
    if (!data || !data.timestamps || data.timestamps.length === 0) {
        console.warn('No risk data available');
        return;
    }
    
    // 获取最新数据点
    const lastIndex = data.timestamps.length - 1;
    const volaxivity = data.volaxivity ? data.volaxivity[lastIndex] : null;
    const volatilitySkew = data.volatility_skew ? data.volatility_skew[lastIndex] : null;
    const putCallRatio = data.put_call_ratio ? data.put_call_ratio[lastIndex] : null;
    const reflexivity = data.reflexivity_indicator ? data.reflexivity_indicator[lastIndex] : null;
    
    // 更新UI值
    updateElementText('volaxivity-value', volaxivity ? volaxivity.toFixed(2) : 'N/A');
    updateElementText('volatility-skew-value', volatilitySkew ? volatilitySkew.toFixed(2) : 'N/A');
    updateElementText('put-call-ratio-value', putCallRatio ? putCallRatio.toFixed(2) : 'N/A');
    updateElementText('reflexivity-value', reflexivity ? (reflexivity * 100).toFixed(2) + '%' : 'N/A');
    
    // 基于时间周期设置阈值
    let volaxivityLevels, skewLevels, pcrLevels, reflexivityLevels;
    
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
        default:
            volaxivityLevels = [20, 30, 40];
            skewLevels = [0.5, 1.0, 1.5];
            pcrLevels = [1.2, 1.5, 2.0];
            reflexivityLevels = [0.3, 0.5, 0.7];
    }
    
    // 更新风险指标可视化
    updateRiskLevelIndicator('volaxivity-level', volaxivity, volaxivityLevels);
    updateRiskLevelIndicator('volatility-skew-level', volatilitySkew, skewLevels);
    updateRiskLevelIndicator('put-call-ratio-level', putCallRatio, pcrLevels);
    updateRiskLevelIndicator('reflexivity-level', reflexivity, reflexivityLevels);
}

// 更新风险等级指标
function updateRiskLevelIndicator(elementId, value, thresholds) {
    const indicator = document.getElementById(elementId);
    if (!indicator) return;
    
    // 移除先前的类
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

// 获取偏离数据
async function fetchDeviationData(showToastOnSuccess = false) {
    console.log('Fetching deviation data...');
    const symbol = document.getElementById('symbol-filter').value;
    const exchange = document.getElementById('exchange-filter').value;
    const optionType = document.getElementById('option-type-filter').value;
    const timePeriod = document.getElementById('time-period-filter').value;
    const days = document.getElementById('days-filter').value;
    const volumeChangeFilter = document.getElementById('volume-change-filter').value;
    const anomalyOnly = document.getElementById('anomaly-only-filter').checked;
    
    // 构建URL参数
    let params = new URLSearchParams({
        symbol: symbol,
        exchange: exchange,
        time_period: timePeriod,
        days: days,
        anomaly_only: anomalyOnly,
        volume_change_filter: volumeChangeFilter
    });
    
    // 仅当选择了特定期权类型时添加参数
    if (optionType) {
        params.append('option_type', optionType);
    }
    
    console.log('Request URL:', `/api/deviation/data?${params.toString()}`);
    
    try {
        const response = await fetch(`/api/deviation/data?${params.toString()}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log(`Received ${data.length} records from API`);
            
            // 如果设置了成交量变化筛选器，确保在前端再次进行筛选
            let filteredData = data;
            if (volumeChangeFilter > 0) {
                // 仅保留成交量变化百分比不为空且大于等于指定值的数据
                filteredData = data.filter(item => 
                    item.volume_change_percent !== null && 
                    item.volume_change_percent >= volumeChangeFilter
                );
                console.log(`Applied volume change filter: ${volumeChangeFilter}%, found ${filteredData.length} matching records out of ${data.length}`);
            }
            
            // 限制处理的数据量以提高性能
            const limitedData = filteredData.length > 500 ? filteredData.slice(0, 500) : filteredData;
            deviationData = filteredData; // 保存筛选后的数据用于导出
            
            // 使用 requestAnimationFrame 来优化渲染性能
            requestAnimationFrame(() => {
                createDeviationChart(limitedData);
                
                // 延迟渲染其他图表和表格
                setTimeout(() => {
                    updateDeviationTable(limitedData);
                    
                    // 进一步延迟渲染比较图表
                    setTimeout(() => {
                        createExchangeComparisonCharts(limitedData);
                        
                        if (showToastOnSuccess) {
                            showToast('Data refreshed successfully', 'success');
                        }
                    }, 100);
                }, 100);
            });
        } else {
            console.error('Error fetching deviation data:', data.message);
            showToast(`Error loading data: ${data.message}`, 'danger');
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showToast('Error connecting to server', 'danger');
    }
}

// 创建偏离图表
function createDeviationChart(data) {
    // 优化: 如果数据量太大，采样以提高性能
    let chartData = data;
    if (data.length > 100) {
        // 采样: 只取每n个数据点中的1个
        const sampleInterval = Math.ceil(data.length / 100);
        chartData = data.filter((_, index) => index % sampleInterval === 0);
        console.log(`Sampled data for chart: ${chartData.length} points from ${data.length} original points`);
    }
    
    // 准备图表数据
    const labels = chartData.map(item => item.timestamp);
    const deviationDataset = {
        label: 'Deviation %',
        data: chartData.map(item => item.deviation_percent),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderWidth: 2,
        fill: false,
        yAxisID: 'y-deviation'
    };
    
    const volumeDataset = {
        label: 'Volume',
        data: chartData.map(item => item.volume),
        borderColor: 'rgba(153, 102, 255, 1)',
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        borderWidth: 1,
        fill: false,
        yAxisID: 'y-volume'
    };
    
    const premiumDataset = {
        label: 'Premium',
        data: chartData.map(item => item.premium),
        borderColor: 'rgba(255, 159, 64, 1)',
        backgroundColor: 'rgba(255, 159, 64, 0.2)',
        borderWidth: 1,
        fill: false,
        yAxisID: 'y-premium'
    };
    
    // 销毁现有图表
    const ctx = document.getElementById('deviation-chart');
    if (deviationChart) {
        deviationChart.destroy();
    }
    
    // 创建新图表
    deviationChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [deviationDataset, volumeDataset, premiumDataset]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    }
                },
                'y-deviation': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Deviation %'
                    }
                },
                'y-volume': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Volume'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                'y-premium': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Premium'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.raw !== null ? context.raw : 'N/A';
                            if (label === 'Deviation %') {
                                return `${label}: ${value.toFixed(2)}%`;
                            } else {
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        }
    });
}

// 更新偏离数据表格
function updateDeviationTable(data) {
    const tableBody = document.getElementById('deviation-data-body');
    if (!tableBody) return;
    
    // 清空表格
    tableBody.innerHTML = '';
    
    // 填充新数据
    if (data.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="10" class="text-center">No data available</td>`;
        tableBody.appendChild(row);
    } else {
        // 限制表格中显示的行数
        const displayData = data.slice(0, 100);
        
        displayData.forEach(item => {
            const row = document.createElement('tr');
            if (item.is_anomaly) {
                row.classList.add('table-warning');
            }
            
            // 格式化数据
            const timestamp = new Date(item.timestamp).toLocaleString();
            const strikePrice = item.strike_price.toFixed(2);
            const marketPrice = item.market_price.toFixed(2);
            const deviationPercent = item.deviation_percent.toFixed(2) + '%';
            const volumeChange = item.volume_change_percent !== null ? item.volume_change_percent.toFixed(2) + '%' : 'N/A';
            const premiumChange = item.premium_change_percent !== null ? item.premium_change_percent.toFixed(2) + '%' : 'N/A';
            const marketPriceChange = item.market_price_change_percent !== null ? item.market_price_change_percent.toFixed(2) + '%' : 'N/A';
            
            // 创建单元格
            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${item.symbol}</td>
                <td>${item.exchange}</td>
                <td>${strikePrice}</td>
                <td>${marketPrice}</td>
                <td>${deviationPercent}</td>
                <td>${item.option_type.toUpperCase()}</td>
                <td>${item.expiration_date}</td>
                <td>${item.volume}</td>
                <td>${volumeChange}</td>
                <td>${item.premium}</td>
                <td>${premiumChange}</td>
                <td>${marketPriceChange}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    // 更新表格计数器
    const countElement = document.getElementById('data-count');
    if (countElement) {
        countElement.textContent = `Showing ${Math.min(data.length, 100)} of ${data.length} records`;
    }
}

// 创建交易所比较图表
function createExchangeComparisonCharts(data) {
    createPCRComparisonChart(data);
    createVolumeDistributionChart(data);
    createPremiumSpreadChart(data);
}

// 创建看跌看涨比率比较图表
function createPCRComparisonChart(data) {
    // 按交易所分组数据
    const exchanges = [...new Set(data.map(item => item.exchange))];
    
    // 计算每个交易所的PCR
    const pcrData = exchanges.map(exchange => {
        const exchangeData = data.filter(item => item.exchange === exchange);
        const calls = exchangeData.filter(item => item.option_type === 'call');
        const puts = exchangeData.filter(item => item.option_type === 'put');
        
        const callVolume = calls.reduce((sum, item) => sum + item.volume, 0);
        const putVolume = puts.reduce((sum, item) => sum + item.volume, 0);
        
        const pcr = callVolume > 0 ? putVolume / callVolume : 0;
        return {
            exchange,
            pcr
        };
    });
    
    // 准备图表数据
    const ctx = document.getElementById('pcr-comparison-chart');
    if (pcrComparisonChart) {
        pcrComparisonChart.destroy();
    }
    
    pcrComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: pcrData.map(item => item.exchange),
            datasets: [{
                label: 'Put/Call Ratio',
                data: pcrData.map(item => item.pcr),
                backgroundColor: [
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(255, 206, 86, 0.6)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'P/C Ratio'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `P/C Ratio: ${context.raw.toFixed(2)}`;
                        }
                    }
                }
            }
        }
    });
}

// 创建成交量分布图表
function createVolumeDistributionChart(data) {
    // 按交易所分组数据
    const exchanges = [...new Set(data.map(item => item.exchange))];
    
    // 计算每个交易所的总成交量
    const volumeData = exchanges.map(exchange => {
        const exchangeData = data.filter(item => item.exchange === exchange);
        const totalVolume = exchangeData.reduce((sum, item) => sum + item.volume, 0);
        return {
            exchange,
            volume: totalVolume
        };
    });
    
    // 准备图表数据
    const ctx = document.getElementById('volume-distribution-chart');
    if (volumeDistributionChart) {
        volumeDistributionChart.destroy();
    }
    
    volumeDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: volumeData.map(item => item.exchange),
            datasets: [{
                label: 'Volume Distribution',
                data: volumeData.map(item => item.volume),
                backgroundColor: [
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(255, 206, 86, 0.6)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(255, 206, 86, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                            const percentage = ((value / total) * 100).toFixed(2);
                            return `Volume: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 创建权利金价差图表
function createPremiumSpreadChart(data) {
    // 按交易所分组数据
    const exchanges = [...new Set(data.map(item => item.exchange))];
    
    // 计算每个交易所的平均权利金
    const premiumData = exchanges.map(exchange => {
        const exchangeData = data.filter(item => item.exchange === exchange);
        const avgPremium = exchangeData.length > 0 ? 
            exchangeData.reduce((sum, item) => sum + item.premium, 0) / exchangeData.length : 0;
        return {
            exchange,
            avgPremium
        };
    });
    
    // 准备图表数据
    const ctx = document.getElementById('premium-spread-chart');
    if (premiumSpreadChart) {
        premiumSpreadChart.destroy();
    }
    
    premiumSpreadChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: premiumData.map(item => item.exchange),
            datasets: [{
                label: 'Avg. Premium',
                data: premiumData.map(item => item.avgPremium),
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(153, 102, 255, 0.6)',
                    'rgba(255, 159, 64, 0.6)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Average Premium'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Avg. Premium: ${context.raw.toFixed(4)}`;
                        }
                    }
                }
            }
        }
    });
}

// 导出CSV
function exportCsv() {
    if (!deviationData || deviationData.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    // 定义CSV头
    const headers = [
        'Timestamp', 'Symbol', 'Exchange', 'Strike Price', 'Market Price', 'Deviation %', 
        'Option Type', 'Expiration Date', 'Volume', 'Volume Change %', 
        'Premium', 'Premium Change %', 'Market Price Change %', 'Is Anomaly'
    ];
    
    // 转换数据为CSV行
    const csvRows = [headers.join(',')];
    
    deviationData.forEach(item => {
        const row = [
            `"${item.timestamp}"`,
            `"${item.symbol}"`,
            `"${item.exchange}"`,
            item.strike_price,
            item.market_price,
            item.deviation_percent,
            `"${item.option_type}"`,
            `"${item.expiration_date}"`,
            item.volume,
            item.volume_change_percent !== null ? item.volume_change_percent : 'N/A',
            item.premium,
            item.premium_change_percent !== null ? item.premium_change_percent : 'N/A',
            item.market_price_change_percent !== null ? item.market_price_change_percent : 'N/A',
            item.is_anomaly ? 'Yes' : 'No'
        ];
        
        csvRows.push(row.join(','));
    });
    
    // 创建CSV内容
    const csvContent = csvRows.join('\n');
    
    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // 设置下载属性
    const symbol = document.getElementById('symbol-filter').value;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.setAttribute('href', url);
    link.setAttribute('download', `deviation_data_${symbol}_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    
    // 添加到文档，触发下载，然后移除
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 确认警报
async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch('/api/deviation/acknowledge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                alert_id: alertId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 成功确认警报后，从UI中移除该警报
            const alertRow = document.querySelector(`tr[data-alert-id="${alertId}"]`);
            if (alertRow) {
                alertRow.remove();
                
                // 检查是否还有警报
                const alertsTable = document.getElementById('active-alerts-body');
                if (alertsTable && alertsTable.children.length === 0) {
                    const alertsCard = alertsTable.closest('.card-body');
                    if (alertsCard) {
                        alertsCard.innerHTML = `
                            <div class="text-center py-4">
                                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                                <p class="lead">No active deviation alerts</p>
                            </div>
                        `;
                    }
                }
                
                showToast('Alert acknowledged successfully', 'success');
            }
        } else {
            showToast(`Error: ${data.message}`, 'danger');
        }
    } catch (error) {
        console.error('Error acknowledging alert:', error);
        showToast('Error connecting to server', 'danger');
    }
}

// 显示通知
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        // 创建容器
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '5';
        document.body.appendChild(container);
    }
    
    // 创建通知元素
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
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
    
    document.getElementById('toast-container').appendChild(toast);
    
    // 初始化和显示通知
    const toastInstance = new bootstrap.Toast(toast, {
        delay: 5000
    });
    toastInstance.show();
    
    // 自动移除
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

// 更新元素文本
function updateElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}