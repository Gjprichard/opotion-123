// 仪表盘脚本
document.addEventListener('DOMContentLoaded', function() {
    // 初始化选项
    const symbol = document.getElementById('symbol-selector').value;
    const timePeriod = document.getElementById('time-period-selector').value;
    
    // 加载初始数据
    loadDashboardData(symbol, timePeriod);
    
    // 设置选择器事件监听
    document.getElementById('symbol-selector').addEventListener('change', function() {
        loadDashboardData(this.value, timePeriod);
    });
    
    document.getElementById('time-period-selector').addEventListener('change', function() {
        loadDashboardData(symbol, this.value);
    });
    
    // 设置刷新按钮事件
    document.getElementById('refresh-btn').addEventListener('click', function() {
        const currentSymbol = document.getElementById('symbol-selector').value;
        const currentTimePeriod = document.getElementById('time-period-selector').value;
        
        // 显示加载指示器
        showSpinner();
        
        // 触发数据刷新
        fetch('/api/refresh-data')
            .then(response => response.json())
            .then(data => {
                // 刷新完成后重新加载仪表盘数据
                loadDashboardData(currentSymbol, currentTimePeriod);
                showToast('数据已更新', 'success');
            })
            .catch(error => {
                console.error('刷新数据时出错:', error);
                showToast('刷新数据失败', 'danger');
                hideSpinner();
            });
    });
});

/**
 * 加载仪表盘数据
 */
function loadDashboardData(symbol, timePeriod) {
    // 显示加载指示器
    showSpinner();
    
    // 更新选择器值（如果是通过按钮调用而不是选择器触发）
    document.getElementById('symbol-selector').value = symbol;
    document.getElementById('time-period-selector').value = timePeriod;
    
    // 获取仪表盘数据
    fetch(`/api/dashboard-data?symbol=${symbol}&time_period=${timePeriod}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应失败');
            }
            return response.json();
        })
        .then(data => {
            // 隐藏加载指示器
            hideSpinner();
            
            // 更新仪表盘组件
            updateDashboardComponents(data);
        })
        .catch(error => {
            console.error('加载仪表盘数据时出错:', error);
            hideSpinner();
            showToast('加载数据失败', 'danger');
            
            // 显示错误消息
            document.getElementById('dashboard-container').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> 
                    加载数据失败。请检查网络连接并重试。
                </div>
            `;
        });
}

/**
 * 更新仪表盘各组件
 */
function updateDashboardComponents(data) {
    // 更新市场概览卡片
    updateMarketOverview(data.current);
    
    // 更新风险指标卡片
    updateRiskIndicators(data.current);
    
    // 更新历史图表
    updateCharts(data.history);
    
    // 更新交易所数据比较
    updateExchangeComparison(data.exchange_data);
    
    // 更新最新警报
    updateLatestAlerts(data.alerts);
}

/**
 * 更新市场概览卡片
 */
function updateMarketOverview(currentData) {
    if (!currentData) return;
    
    // 设置当前价格和变化
    const priceChangeClass = currentData.price_change >= 0 ? 'text-success' : 'text-danger';
    const priceChangeIcon = currentData.price_change >= 0 ? 'fa-caret-up' : 'fa-caret-down';
    
    document.getElementById('current-price').textContent = formatNumber(currentData.price);
    document.getElementById('price-change').innerHTML = `
        <span class="${priceChangeClass}">
            <i class="fas ${priceChangeIcon}"></i>
            ${formatNumber(Math.abs(currentData.price_change), 2)}%
        </span>
    `;
    
    // 设置市场情绪
    const sentimentClass = getSentimentClass(currentData.market_sentiment);
    document.getElementById('market-sentiment').innerHTML = `
        <span class="${sentimentClass}">
            ${getSentimentText(currentData.market_sentiment)}
        </span>
    `;
    
    // 设置看跌/看涨比率
    const pcrClass = getPCRClass(currentData.put_call_ratio);
    document.getElementById('pcr-value').innerHTML = `
        <span class="${pcrClass}">${formatNumber(currentData.put_call_ratio, 2)}</span>
    `;
    
    // 设置总交易量
    document.getElementById('total-volume').textContent = formatNumber(currentData.total_volume, 0);
    
    // 设置最后更新时间
    document.getElementById('last-updated').textContent = formatDate(currentData.timestamp);
}

/**
 * 更新风险指标卡片
 */
function updateRiskIndicators(currentData) {
    if (!currentData) return;
    
    // 设置波动率指数
    const volIndex = document.getElementById('volatility-index');
    volIndex.textContent = formatNumber(currentData.volaxivity * 100, 2) + '%';
    volIndex.className = getRiskClass(currentData.volaxivity, 0.2, 0.3, 0.4);
    
    // 设置波动率偏斜
    const volSkew = document.getElementById('volatility-skew');
    volSkew.textContent = formatNumber(currentData.volatility_skew, 3);
    volSkew.className = getInvertedRiskClass(Math.abs(currentData.volatility_skew), 0.05, 0.1, 0.2);
    
    // 设置Delta敞口
    const deltaExp = document.getElementById('delta-exposure');
    if (deltaExp) {
        deltaExp.textContent = formatNumber(currentData.delta_exposure, 3);
        deltaExp.className = getInvertedRiskClass(Math.abs(currentData.delta_exposure), 0.1, 0.3, 0.5);
    }
    
    // 设置Gamma敞口
    const gammaExp = document.getElementById('gamma-exposure');
    if (gammaExp) {
        gammaExp.textContent = formatNumber(currentData.gamma_exposure, 5);
        gammaExp.className = getInvertedRiskClass(Math.abs(currentData.gamma_exposure), 0.0001, 0.0005, 0.001);
    }
    
    // 设置Vega敞口
    const vegaExp = document.getElementById('vega-exposure');
    if (vegaExp) {
        vegaExp.textContent = formatNumber(currentData.vega_exposure, 2);
        vegaExp.className = getInvertedRiskClass(Math.abs(currentData.vega_exposure), 5, 10, 15);
    }
    
    // 设置整体风险等级
    const riskLevel = document.getElementById('risk-level');
    riskLevel.textContent = getRiskLevelText(currentData.risk_level);
    riskLevel.className = getRiskLevelClass(currentData.risk_level);
}

/**
 * 更新历史图表
 */
function updateCharts(historyData) {
    if (!historyData || historyData.length === 0) {
        handleChartError(document.getElementById('volatility-chart-container'), '没有历史数据可供显示');
        handleChartError(document.getElementById('pcr-chart-container'), '没有历史数据可供显示');
        handleChartError(document.getElementById('greeks-chart-container'), '没有历史数据可供显示');
        handleChartError(document.getElementById('risk-chart-container'), '没有历史数据可供显示');
        return;
    }
    
    // 处理图表数据
    const timestamps = historyData.map(d => formatDate(d.timestamp));
    const volIndex = historyData.map(d => d.volaxivity);
    const volSkew = historyData.map(d => d.volatility_skew);
    const pcrValues = historyData.map(d => d.put_call_ratio);
    const priceValues = historyData.map(d => d.price || 0);
    const deltaValues = historyData.map(d => d.delta_exposure || 0);
    const gammaValues = historyData.map(d => d.gamma_exposure || 0);
    const vegaValues = historyData.map(d => d.vega_exposure || 0);
    const riskLevels = historyData.map(d => d.risk_level || 'medium');
    
    try {
        // 波动率图表
        const volCtx = document.getElementById('volatility-chart').getContext('2d');
        new Chart(volCtx, getVolatilityChartConfig(timestamps, volIndex, volSkew));
        
        // PCR图表
        const pcrCtx = document.getElementById('pcr-chart').getContext('2d');
        new Chart(pcrCtx, getPCRChartConfig(timestamps, pcrValues, priceValues));
        
        // 希腊字母图表
        const greeksCtx = document.getElementById('greeks-chart').getContext('2d');
        new Chart(greeksCtx, getGreeksChartConfig(timestamps, deltaValues, gammaValues, vegaValues));
        
        // 风险等级图表
        const riskCtx = document.getElementById('risk-chart').getContext('2d');
        new Chart(riskCtx, getRiskLevelChartConfig(timestamps, riskLevels));
    } catch (error) {
        console.error('创建图表时出错:', error);
        handleChartError(document.getElementById('charts-container'), '创建图表时发生错误');
    }
}

/**
 * 更新交易所数据比较
 */
function updateExchangeComparison(exchangeData) {
    if (!exchangeData || Object.keys(exchangeData).length === 0) {
        handleChartError(document.getElementById('exchange-comparison-container'), '没有交易所数据可供比较');
        return;
    }
    
    try {
        // 提取交易所数据
        const exchanges = Object.keys(exchangeData);
        const pcrValues = exchanges.map(e => exchangeData[e].ratio || 1.0);
        
        // 绘制交易所比较图表
        const exchangeCtx = document.getElementById('exchange-comparison-chart').getContext('2d');
        new Chart(exchangeCtx, getExchangePCRComparisonConfig(exchanges, pcrValues));
        
        // 绘制看涨/看跌成交量分布图
        const volumeCtx = document.getElementById('volume-distribution-chart').getContext('2d');
        let totalCallVolume = 0;
        let totalPutVolume = 0;
        
        for (const exchange of exchanges) {
            totalCallVolume += exchangeData[exchange].call_volume || 0;
            totalPutVolume += exchangeData[exchange].put_volume || 0;
        }
        
        new Chart(volumeCtx, getVolumeDistributionConfig(totalCallVolume, totalPutVolume));
        
        // 更新交易所详细数据表格
        const tableBody = document.getElementById('exchange-detail-table-body');
        if (tableBody) {
            tableBody.innerHTML = '';
            
            for (const exchange of exchanges) {
                const data = exchangeData[exchange];
                const row = document.createElement('tr');
                
                row.innerHTML = `
                    <td class="text-capitalize">${exchange}</td>
                    <td>${formatNumber(data.call_volume || 0, 0)}</td>
                    <td>${formatNumber(data.put_volume || 0, 0)}</td>
                    <td class="${getPCRClass(data.ratio)}">${formatNumber(data.ratio || 1.0, 2)}</td>
                `;
                
                tableBody.appendChild(row);
            }
        }
    } catch (error) {
        console.error('创建交易所比较图表时出错:', error);
        handleChartError(document.getElementById('exchange-comparison-container'), '创建图表时发生错误');
    }
}

/**
 * 更新最新警报
 */
function updateLatestAlerts(alerts) {
    const alertsContainer = document.getElementById('latest-alerts');
    
    if (!alerts || alerts.length === 0) {
        alertsContainer.innerHTML = '<div class="alert alert-info">目前没有警报</div>';
        return;
    }
    
    // 限制最多显示5条警报
    const latestAlerts = alerts.slice(0, 5);
    let alertsHtml = '';
    
    for (const alert of latestAlerts) {
        const alertClass = getAlertLevelClass(alert.level);
        const alertTime = formatDate(alert.timestamp);
        
        alertsHtml += `
            <div class="alert ${alertClass} d-flex justify-content-between align-items-center">
                <div>
                    <strong>${alert.indicator_name}:</strong> ${alert.message}
                </div>
                <small class="text-muted">${alertTime}</small>
            </div>
        `;
    }
    
    alertsContainer.innerHTML = alertsHtml;
}

/**
 * 辅助函数: 显示加载指示器
 */
function showSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.classList.remove('d-none');
}

/**
 * 辅助函数: 隐藏加载指示器
 */
function hideSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.classList.add('d-none');
}

/**
 * 辅助函数: 显示提示消息
 */
function showToast(message, type = 'info') {
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
    
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        // 自动删除已显示的toast
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
}

/**
 * 辅助函数: 获取市场情绪样式类
 */
function getSentimentClass(sentiment) {
    if (sentiment === 'bullish') return 'text-success';
    if (sentiment === 'bearish') return 'text-danger';
    return 'text-warning';
}

/**
 * 辅助函数: 获取市场情绪文本
 */
function getSentimentText(sentiment) {
    if (sentiment === 'bullish') return '看涨';
    if (sentiment === 'bearish') return '看跌';
    return '中性';
}

/**
 * 辅助函数: 获取看跌/看涨比率样式类
 */
function getPCRClass(pcr) {
    if (pcr > 1.2) return 'text-danger';
    if (pcr < 0.8) return 'text-success';
    return 'text-warning';
}

/**
 * 辅助函数: 获取风险等级样式类
 */
function getRiskClass(value, medium, high, extreme) {
    if (value < medium) return 'text-success';
    if (value < high) return 'text-warning';
    if (value < extreme) return 'text-danger';
    return 'text-danger fw-bold';
}

/**
 * 辅助函数: 获取反转的风险等级样式类（越低越好）
 */
function getInvertedRiskClass(value, medium, high, extreme) {
    if (value < medium) return 'text-success';
    if (value < high) return 'text-warning';
    if (value < extreme) return 'text-danger';
    return 'text-danger fw-bold';
}

/**
 * 辅助函数: 获取风险等级文本
 */
function getRiskLevelText(level) {
    if (level === 'low') return '低';
    if (level === 'medium') return '中';
    if (level === 'high') return '高';
    if (level === 'extreme') return '极高';
    return '未知';
}

/**
 * 辅助函数: 获取风险等级样式类
 */
function getRiskLevelClass(level) {
    if (level === 'low') return 'text-success';
    if (level === 'medium') return 'text-warning';
    if (level === 'high') return 'text-danger';
    if (level === 'extreme') return 'text-danger fw-bold';
    return 'text-muted';
}

/**
 * 辅助函数: 获取警报等级样式类
 */
function getAlertLevelClass(level) {
    if (level === 'attention') return 'alert-info';
    if (level === 'warning') return 'alert-warning';
    if (level === 'severe') return 'alert-danger';
    return 'alert-secondary';
}