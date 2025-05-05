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
        volume_change_filter: volumeChangeFilter,
        include_stats: true  // 请求包含统计数据
    });
    
    // 仅当选择了特定期权类型时添加参数
    if (optionType) {
        params.append('option_type', optionType);
    }
    
    console.log('Request URL:', `/api/deviation/data?${params.toString()}`);
    
    try {
        const response = await fetch(`/api/deviation/data?${params.toString()}`);
        const responseData = await response.json();
        
        if (response.ok) {
            // 检查响应数据格式
            let deviations = [];
            let statistics = {};
            
            // 处理新的响应格式(包含统计数据的对象)或旧格式(纯数组)
            if (responseData && typeof responseData === 'object' && responseData.deviations) {
                // 新格式
                deviations = responseData.deviations;
                statistics = responseData.statistics || {};
                console.log(`Received ${deviations.length} records and statistics from API`);
            } else if (Array.isArray(responseData)) {
                // 旧格式(为了兼容)
                deviations = responseData;
                console.log(`Received ${deviations.length} records from API (legacy format)`);
                // 在前端计算统计数据
                statistics = calculateDataStatistics(deviations);
            } else {
                console.error('Unexpected response format:', responseData);
                showToast('Unexpected data format received', 'warning');
                return;
            }
            
            // 如果设置了成交量变化筛选器，确保在前端再次进行筛选
            let filteredData = deviations;
            if (volumeChangeFilter > 0) {
                // 仅保留成交量变化百分比不为空且大于等于指定值的数据
                filteredData = deviations.filter(item => 
                    item.volume_change_percent !== null && 
                    item.volume_change_percent >= volumeChangeFilter
                );
                console.log(`Applied volume change filter: ${volumeChangeFilter}%, found ${filteredData.length} matching records out of ${deviations.length}`);
            }
            
            // 限制处理的数据量以提高性能
            const limitedData = filteredData.length > 500 ? filteredData.slice(0, 500) : filteredData;
            deviationData = filteredData; // 保存筛选后的数据用于导出
            
            // 使用 requestAnimationFrame 来优化渲染性能
            requestAnimationFrame(() => {
                // 如果统计数据可用，直接使用后端提供的统计数据
                if (Object.keys(statistics).length > 0) {
                    // 更新统计面板
                    updateStatisticsPanel(statistics);
                    
                    // 创建偏离图表
                    createDeviationChart(limitedData, statistics);
                    
                    // 创建趋势分析图
                    createTrendAnalysisChart(limitedData, statistics);
                } else {
                    // 否则使用前端计算的统计数据
                    createDeviationChart(limitedData);
                }
                
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
            console.error('Error fetching deviation data:', responseData.message);
            showToast(`Error loading data: ${responseData.message}`, 'danger');
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showToast('Error connecting to server', 'danger');
    }
}

// 创建偏离图表 - 优化版
function createDeviationChart(data, externalStats = null) {
    // 使用外部统计数据或计算新的统计数据
    const stats = externalStats || calculateDataStatistics(data);
    
    // 创建散点图数据
    const scatterData = prepareScatterData(data);
    
    // 销毁现有图表
    const ctx = document.getElementById('deviation-chart');
    if (deviationChart) {
        deviationChart.destroy();
    }
    
    // 创建增强型散点图
    deviationChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: scatterData
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `期权执行价偏离分布图 (${stats.totalPoints || data.length}个数据点)`
                },
                subtitle: {
                    display: true,
                    text: `平均偏离率: ${(stats.avgDeviation || 0).toFixed(2)}%, 平均成交量变化: ${(stats.avgVolumeChange || 0).toFixed(2)}%`
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            if (point.isTrendLine) {
                                return `趋势线: ${point.trendLabel || ''}`;
                            }
                            return `${point.symbol} ${point.optionTypeDisplay}: 执行价 ${point.strike_price.toFixed(2)}, 偏离 ${point.deviation_percent.toFixed(2)}%, 成交量变化 ${point.volume_change_percent ? point.volume_change_percent.toFixed(1) : 'N/A'}%`;
                        },
                        footer: function(tooltipItems) {
                            const item = tooltipItems[0];
                            if (item.raw.isTrendLine) return '';
                            
                            // 为异常点添加额外信息
                            if (item.raw.is_anomaly) {
                                let level = '';
                                switch(item.raw.anomaly_level) {
                                    case 'attention': level = '关注级'; break;
                                    case 'warning': level = '警告级'; break;
                                    case 'severe': level = '严重级'; break;
                                }
                                return `异常级别: ${level}`;
                            }
                            return '';
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: '偏离百分比 (%)'
                    },
                    min: 0,
                    max: 10,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '成交量变化率 (%)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            animation: {
                duration: 1000
            }
        }
    });
    
    // 如果统计面板不是由外部更新的，则在这里更新
    if (!externalStats) {
        updateStatisticsPanel(stats);
        createTrendAnalysisChart(data, stats);
    }
}

// 准备散点图数据
function prepareScatterData(data) {
    // 按期权类型和异常级别分组
    const callData = [];
    const putData = [];
    const callAnomalyData = [];
    const putAnomalyData = [];
    
    // 遍历数据
    data.forEach(item => {
        // 基本点数据
        const point = {
            x: item.deviation_percent,
            y: item.volume_change_percent || 0,
            symbol: item.symbol,
            strike_price: item.strike_price,
            optionTypeDisplay: item.option_type === 'call' ? '看涨' : '看跌',
            option_type: item.option_type,
            deviation_percent: item.deviation_percent,
            volume_change_percent: item.volume_change_percent,
            is_anomaly: item.is_anomaly,
            anomaly_level: item.anomaly_level,
            premium: item.premium,
            premium_change_percent: item.premium_change_percent
        };
        
        // 根据期权类型和异常状态分组
        if (item.option_type === 'call') {
            if (item.is_anomaly) {
                callAnomalyData.push(point);
            } else {
                callData.push(point);
            }
        } else {
            if (item.is_anomaly) {
                putAnomalyData.push(point);
            } else {
                putData.push(point);
            }
        }
    });
    
    // 计算趋势线
    const callTrendLine = calculateTrendLine(callData.concat(callAnomalyData));
    const putTrendLine = calculateTrendLine(putData.concat(putAnomalyData));
    
    // 创建数据集
    return [
        {
            label: '看涨期权',
            data: callData,
            backgroundColor: 'rgba(54, 162, 235, 0.5)',
            borderColor: 'rgb(54, 162, 235)',
            pointRadius: 4,
            pointHoverRadius: 6
        },
        {
            label: '看跌期权',
            data: putData,
            backgroundColor: 'rgba(75, 192, 192, 0.5)',
            borderColor: 'rgb(75, 192, 192)', 
            pointRadius: 4,
            pointHoverRadius: 6
        },
        {
            label: '看涨期权 (异常)',
            data: callAnomalyData,
            backgroundColor: function(context) {
                const level = context.raw.anomaly_level;
                switch(level) {
                    case 'attention': return 'rgba(255, 205, 86, 0.7)';
                    case 'warning': return 'rgba(255, 159, 64, 0.7)';
                    case 'severe': return 'rgba(255, 99, 132, 0.7)';
                    default: return 'rgba(255, 99, 132, 0.7)';
                }
            },
            borderColor: function(context) {
                const level = context.raw.anomaly_level;
                switch(level) {
                    case 'attention': return 'rgb(255, 205, 86)';
                    case 'warning': return 'rgb(255, 159, 64)';
                    case 'severe': return 'rgb(255, 99, 132)';
                    default: return 'rgb(255, 99, 132)';
                }
            },
            pointRadius: 6,
            pointHoverRadius: 8
        },
        {
            label: '看跌期权 (异常)',
            data: putAnomalyData,
            backgroundColor: function(context) {
                const level = context.raw.anomaly_level;
                switch(level) {
                    case 'attention': return 'rgba(255, 205, 86, 0.7)';
                    case 'warning': return 'rgba(255, 159, 64, 0.7)';
                    case 'severe': return 'rgba(255, 99, 132, 0.7)';
                    default: return 'rgba(255, 99, 132, 0.7)';
                }
            },
            borderColor: function(context) {
                const level = context.raw.anomaly_level;
                switch(level) {
                    case 'attention': return 'rgb(255, 205, 86)';
                    case 'warning': return 'rgb(255, 159, 64)';
                    case 'severe': return 'rgb(255, 99, 132)';
                    default: return 'rgb(255, 99, 132)';
                }
            },
            pointRadius: 6,
            pointHoverRadius: 8
        },
        {
            label: '看涨期权趋势',
            data: callTrendLine,
            type: 'line',
            borderColor: 'rgba(54, 162, 235, 0.8)',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false
        },
        {
            label: '看跌期权趋势',
            data: putTrendLine,
            type: 'line',
            borderColor: 'rgba(75, 192, 192, 0.8)',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false
        }
    ];
}

// 计算数据统计值
function calculateDataStatistics(data) {
    // 基本统计
    const totalPoints = data.length;
    let totalDeviation = 0;
    let totalVolumeChange = 0;
    let validVolumePoints = 0;
    
    // 异常统计
    let anomalyPoints = 0;
    let attentionCount = 0;
    let warningCount = 0;
    let severeCount = 0;
    
    // 期权类型统计
    let callOptions = 0;
    let putOptions = 0;
    let callVolume = 0;
    let putVolume = 0;
    
    // 偏离区间统计
    let deviationRanges = {
        '0-2%': 0,
        '2-4%': 0,
        '4-6%': 0,
        '6-8%': 0,
        '8-10%': 0
    };
    
    // 分析数据
    data.forEach(item => {
        // 基本统计
        totalDeviation += item.deviation_percent;
        
        if (item.volume_change_percent !== null) {
            totalVolumeChange += item.volume_change_percent;
            validVolumePoints++;
        }
        
        // 期权类型统计
        if (item.option_type === 'call') {
            callOptions++;
            callVolume += item.volume || 0;
        } else {
            putOptions++;
            putVolume += item.volume || 0;
        }
        
        // 异常统计
        if (item.is_anomaly) {
            anomalyPoints++;
            
            switch(item.anomaly_level) {
                case 'attention': attentionCount++; break;
                case 'warning': warningCount++; break;
                case 'severe': severeCount++; break;
            }
        }
        
        // 偏离区间统计
        const dev = item.deviation_percent;
        if (dev < 2) {
            deviationRanges['0-2%']++;
        } else if (dev < 4) {
            deviationRanges['2-4%']++;
        } else if (dev < 6) {
            deviationRanges['4-6%']++;
        } else if (dev < 8) {
            deviationRanges['6-8%']++;
        } else {
            deviationRanges['8-10%']++;
        }
    });
    
    // 计算平均值
    const avgDeviation = totalPoints > 0 ? totalDeviation / totalPoints : 0;
    const avgVolumeChange = validVolumePoints > 0 ? totalVolumeChange / validVolumePoints : 0;
    const putCallRatio = callOptions > 0 ? putOptions / callOptions : 0;
    const volumePutCallRatio = callVolume > 0 ? putVolume / callVolume : 0;
    const anomalyPercentage = totalPoints > 0 ? (anomalyPoints / totalPoints) * 100 : 0;
    
    // 返回统计结果
    return {
        totalPoints,
        avgDeviation,
        avgVolumeChange,
        anomalyPoints,
        anomalyPercentage,
        putCallRatio,
        volumePutCallRatio,
        callOptions,
        putOptions,
        callVolume,
        putVolume,
        attentionCount,
        warningCount,
        severeCount,
        deviationRanges
    };
}

// 计算趋势线数据
function calculateTrendLine(points) {
    if (points.length < 5) return [];  // 数据点太少，不计算趋势
    
    // 提取有效数据点
    const validPoints = points.filter(p => 
        p.x !== null && p.y !== null && !isNaN(p.x) && !isNaN(p.y)
    );
    
    if (validPoints.length < 5) return [];
    
    // 计算平均值
    let sumX = 0, sumY = 0;
    validPoints.forEach(point => {
        sumX += point.x;
        sumY += point.y;
    });
    
    const avgX = sumX / validPoints.length;
    const avgY = sumY / validPoints.length;
    
    // 计算斜率和截距
    let numerator = 0, denominator = 0;
    validPoints.forEach(point => {
        numerator += (point.x - avgX) * (point.y - avgY);
        denominator += Math.pow(point.x - avgX, 2);
    });
    
    // 避免除以零
    if (Math.abs(denominator) < 0.001) return [];
    
    const slope = numerator / denominator;
    const intercept = avgY - slope * avgX;
    
    // 生成趋势线数据点
    const trendPoints = [];
    
    // 在x轴上生成数据点
    for (let x = 0; x <= 10; x += 0.5) {
        trendPoints.push({
            x: x,
            y: slope * x + intercept,
            isTrendLine: true,
            trendLabel: `斜率: ${slope.toFixed(2)}`
        });
    }
    
    return trendPoints;
}

// 更新统计面板
function updateStatisticsPanel(stats) {
    // 获取统计面板元素
    const statsPanelElement = document.getElementById('stats-panel');
    if (!statsPanelElement) return;
    
    // 创建统计内容
    let statsHtml = `
        <div class="card mb-4">
            <div class="card-header py-3 d-flex justify-content-between align-items-center">
                <h6 class="m-0 font-weight-bold text-primary">数据统计</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6 class="font-weight-bold">基本统计</h6>
                        <table class="table table-sm">
                            <tr>
                                <th>总数据点</th>
                                <td>${stats.totalPoints}</td>
                            </tr>
                            <tr>
                                <th>平均偏离率</th>
                                <td>${stats.avgDeviation.toFixed(2)}%</td>
                            </tr>
                            <tr>
                                <th>平均成交量变化</th>
                                <td>${stats.avgVolumeChange.toFixed(2)}%</td>
                            </tr>
                            <tr>
                                <th>看跌/看涨比例(数量)</th>
                                <td>${stats.putCallRatio.toFixed(2)} (${stats.putOptions}/${stats.callOptions})</td>
                            </tr>
                            <tr>
                                <th>看跌/看涨比例(成交量)</th>
                                <td>${stats.volumePutCallRatio.toFixed(2)} (${stats.putVolume}/${stats.callVolume})</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6 class="font-weight-bold">异常统计</h6>
                        <table class="table table-sm">
                            <tr>
                                <th>异常数据点</th>
                                <td>${stats.anomalyPoints} (${stats.anomalyPercentage.toFixed(1)}%)</td>
                            </tr>
                            <tr>
                                <th>关注级别</th>
                                <td>${stats.attentionCount}</td>
                            </tr>
                            <tr>
                                <th>警告级别</th>
                                <td>${stats.warningCount}</td>
                            </tr>
                            <tr>
                                <th>严重级别</th>
                                <td>${stats.severeCount}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        <h6 class="font-weight-bold">偏离分布</h6>
                        <div class="progress">
                            <div class="progress-bar bg-success" role="progressbar" style="width: ${calculatePercentage(stats.deviationRanges['0-2%'], stats.totalPoints)}%" 
                                title="0-2%: ${stats.deviationRanges['0-2%']}个数据点">0-2%</div>
                            <div class="progress-bar bg-info" role="progressbar" style="width: ${calculatePercentage(stats.deviationRanges['2-4%'], stats.totalPoints)}%" 
                                title="2-4%: ${stats.deviationRanges['2-4%']}个数据点">2-4%</div>
                            <div class="progress-bar bg-primary" role="progressbar" style="width: ${calculatePercentage(stats.deviationRanges['4-6%'], stats.totalPoints)}%" 
                                title="4-6%: ${stats.deviationRanges['4-6%']}个数据点">4-6%</div>
                            <div class="progress-bar bg-warning" role="progressbar" style="width: ${calculatePercentage(stats.deviationRanges['6-8%'], stats.totalPoints)}%" 
                                title="6-8%: ${stats.deviationRanges['6-8%']}个数据点">6-8%</div>
                            <div class="progress-bar bg-danger" role="progressbar" style="width: ${calculatePercentage(stats.deviationRanges['8-10%'], stats.totalPoints)}%" 
                                title="8-10%: ${stats.deviationRanges['8-10%']}个数据点">8-10%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 更新面板内容
    statsPanelElement.innerHTML = statsHtml;
}

// 辅助函数 - 计算百分比
function calculatePercentage(value, total) {
    if (total === 0) return 0;
    return (value / total * 100).toFixed(1);
}

// 创建趋势分析图
function createTrendAnalysisChart(data, stats) {
    // 获取趋势分析图元素
    const trendChartElement = document.getElementById('trend-analysis-chart');
    if (!trendChartElement || !data.length) return;
    
    // 根据时间重新组织数据
    const timeSeriesData = organizeTimeSeriesData(data);
    
    // 销毁现有图表
    if (window.trendAnalysisChart) {
        window.trendAnalysisChart.destroy();
    }
    
    // 创建数据集
    const datasets = [
        {
            label: '成交量',
            data: timeSeriesData.map(d => d.totalVolume),
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            yAxisID: 'y-volume',
            fill: true
        },
        {
            label: '异常数量',
            data: timeSeriesData.map(d => d.anomalyCount),
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            yAxisID: 'y-anomaly',
            fill: true
        },
        {
            label: '看跌/看涨比率',
            data: timeSeriesData.map(d => d.putCallRatio),
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'transparent',
            yAxisID: 'y-ratio',
            type: 'line'
        }
    ];
    
    // 创建图表
    window.trendAnalysisChart = new Chart(trendChartElement, {
        type: 'bar',
        data: {
            labels: timeSeriesData.map(d => d.timeLabel),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '期权成交量和异常趋势分析'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                'y-volume': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '成交量'
                    }
                },
                'y-anomaly': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '异常数量'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                'y-ratio': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '看跌/看涨比率'
                    },
                    min: 0,
                    max: 3,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

// 按时间组织数据
function organizeTimeSeriesData(data) {
    // 按小时分组数据
    const hourlyData = {};
    
    data.forEach(item => {
        const date = new Date(item.timestamp);
        const hourKey = `${date.getFullYear()}-${(date.getMonth()+1).toString().padStart(2,'0')}-${date.getDate().toString().padStart(2,'0')} ${date.getHours().toString().padStart(2,'0')}:00`;
        
        if (!hourlyData[hourKey]) {
            hourlyData[hourKey] = {
                timeLabel: hourKey,
                totalVolume: 0,
                callVolume: 0,
                putVolume: 0,
                anomalyCount: 0,
                dataPoints: 0
            };
        }
        
        // 累加数据
        hourlyData[hourKey].dataPoints++;
        hourlyData[hourKey].totalVolume += item.volume || 0;
        
        if (item.option_type === 'call') {
            hourlyData[hourKey].callVolume += item.volume || 0;
        } else {
            hourlyData[hourKey].putVolume += item.volume || 0;
        }
        
        if (item.is_anomaly) {
            hourlyData[hourKey].anomalyCount++;
        }
    });
    
    // 计算比率并转换为数组
    const timeSeriesArray = Object.values(hourlyData).map(hour => {
        return {
            ...hour,
            putCallRatio: hour.callVolume > 0 ? hour.putVolume / hour.callVolume : 0
        };
    });
    
    // 按时间排序
    timeSeriesArray.sort((a, b) => new Date(a.timeLabel) - new Date(b.timeLabel));
    
    // 限制数据点数量以提高性能
    const maxPoints = 24; // 显示最近24小时
    if (timeSeriesArray.length > maxPoints) {
        return timeSeriesArray.slice(timeSeriesArray.length - maxPoints);
    }
    
    return timeSeriesArray;
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