// 图表处理脚本

// 图表配置常量
const CHART_COLORS = {
    // 主要颜色
    primary: 'rgba(75, 192, 192, 1)',
    secondary: 'rgba(54, 162, 235, 1)',
    danger: 'rgba(255, 99, 132, 1)',
    warning: 'rgba(255, 159, 64, 1)',
    purple: 'rgba(153, 102, 255, 1)',
    gray: 'rgba(201, 203, 207, 1)',
    
    // 填充颜色
    primaryFill: 'rgba(75, 192, 192, 0.2)',
    secondaryFill: 'rgba(54, 162, 235, 0.2)',
    dangerFill: 'rgba(255, 99, 132, 0.2)',
    warningFill: 'rgba(255, 159, 64, 0.2)',
    purpleFill: 'rgba(153, 102, 255, 0.2)',
    grayFill: 'rgba(201, 203, 207, 0.2)'
};

// 日期格式化
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// 数值格式化
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return '--';
    return parseFloat(value).toFixed(decimals);
}

// 获取波动率图表配置
function getVolatilityChartConfig(timestamps, volatilityIndex, volatilitySkew) {
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '波动率指数',
                    data: volatilityIndex,
                    borderColor: CHART_COLORS.primary,
                    backgroundColor: CHART_COLORS.primaryFill,
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: '波动率偏斜',
                    data: volatilitySkew,
                    borderColor: CHART_COLORS.danger,
                    backgroundColor: CHART_COLORS.dangerFill,
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            stacked: false,
            plugins: {
                title: {
                    display: false,
                    text: '波动率趋势'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '波动率指数'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    title: {
                        display: true,
                        text: '波动率偏斜'
                    }
                }
            }
        }
    };
}

// 获取PCR图表配置
function getPCRChartConfig(timestamps, pcrValues, priceValues) {
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '看跌/看涨比率',
                    data: pcrValues,
                    borderColor: CHART_COLORS.secondary,
                    backgroundColor: CHART_COLORS.secondaryFill,
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: '价格',
                    data: priceValues,
                    borderColor: CHART_COLORS.warning,
                    backgroundColor: CHART_COLORS.warningFill,
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            stacked: false,
            plugins: {
                title: {
                    display: false,
                    text: '看跌/看涨比率趋势'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '看跌/看涨比率'
                    },
                    suggestedMin: 0.5,
                    suggestedMax: 1.5
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    title: {
                        display: true,
                        text: '价格'
                    }
                }
            }
        }
    };
}

// 获取希腊字母图表配置
function getGreeksChartConfig(timestamps, deltaValues, gammaValues, vegaValues) {
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: 'Delta敞口',
                    data: deltaValues,
                    borderColor: CHART_COLORS.secondary,
                    backgroundColor: CHART_COLORS.secondaryFill,
                    borderWidth: 2,
                    tension: 0.3
                },
                {
                    label: 'Gamma敞口',
                    data: gammaValues,
                    borderColor: CHART_COLORS.purple,
                    backgroundColor: CHART_COLORS.purpleFill,
                    borderWidth: 2,
                    tension: 0.3
                },
                {
                    label: 'Vega敞口',
                    data: vegaValues,
                    borderColor: CHART_COLORS.warning,
                    backgroundColor: CHART_COLORS.warningFill,
                    borderWidth: 2,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: false,
                    text: '希腊字母敞口趋势'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '敞口值'
                    }
                }
            }
        }
    };
}

// 获取风险等级图表配置
function getRiskLevelChartConfig(timestamps, riskValues) {
    // 将风险等级文本转换为数值
    const numericRiskValues = riskValues.map(level => {
        if (level === 'low') return 0;
        if (level === 'medium') return 1;
        if (level === 'high') return 2;
        if (level === 'extreme') return 3;
        return 1; // 默认中等风险
    });
    
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: '风险等级',
                data: numericRiskValues,
                borderColor: CHART_COLORS.danger,
                backgroundColor: CHART_COLORS.dangerFill,
                borderWidth: 2,
                tension: 0,
                stepped: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: false,
                    text: '风险等级趋势'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            let riskText = '';
                            if (value === 0) riskText = '低风险';
                            else if (value === 1) riskText = '中等风险';
                            else if (value === 2) riskText = '高风险';
                            else if (value === 3) riskText = '极高风险';
                            return riskText;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    min: 0,
                    max: 3,
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            if (value === 0) return '低';
                            if (value === 1) return '中';
                            if (value === 2) return '高';
                            if (value === 3) return '极高';
                            return '';
                        }
                    },
                    title: {
                        display: true,
                        text: '风险等级'
                    }
                }
            }
        }
    };
}

// 获取交易所PCR比较图表配置
function getExchangePCRComparisonConfig(exchanges, pcrValues) {
    // 基于交易所设置颜色
    const backgroundColors = exchanges.map(exchange => {
        if (exchange === 'deribit') return CHART_COLORS.primaryFill;
        if (exchange === 'binance') return CHART_COLORS.warningFill;
        if (exchange === 'okx') return CHART_COLORS.secondaryFill;
        return CHART_COLORS.grayFill;
    });
    
    const borderColors = exchanges.map(exchange => {
        if (exchange === 'deribit') return CHART_COLORS.primary;
        if (exchange === 'binance') return CHART_COLORS.warning;
        if (exchange === 'okx') return CHART_COLORS.secondary;
        return CHART_COLORS.gray;
    });
    
    // 格式化交易所名称
    const formattedExchanges = exchanges.map(e => 
        e.charAt(0).toUpperCase() + e.slice(1)
    );
    
    return {
        type: 'bar',
        data: {
            labels: formattedExchanges,
            datasets: [{
                label: '看跌/看涨比率',
                data: pcrValues,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false,
                    text: '交易所看跌/看涨比率比较'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            let sentiment = '中性';
                            
                            if (value > 1.2) sentiment = '偏空';
                            else if (value < 0.8) sentiment = '偏多';
                            
                            return `PCR: ${value.toFixed(2)} (${sentiment})`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '比率值'
                    }
                }
            }
        }
    };
}

// 获取成交量分布图表配置
function getVolumeDistributionConfig(callVolume, putVolume) {
    return {
        type: 'doughnut',
        data: {
            labels: ['看涨期权成交量', '看跌期权成交量'],
            datasets: [{
                data: [callVolume, putVolume],
                backgroundColor: [
                    CHART_COLORS.primaryFill,
                    CHART_COLORS.dangerFill
                ],
                borderColor: [
                    CHART_COLORS.primary,
                    CHART_COLORS.danger
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = callVolume + putVolume;
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
}

// 错误处理函数
function handleChartError(chartContainer, errorMessage) {
    console.error(`图表加载错误: ${errorMessage}`);
    
    // 显示错误信息
    const errorHtml = `
        <div class="chart-error text-center p-3">
            <i class="fas fa-exclamation-triangle text-warning mb-2" style="font-size: 2rem;"></i>
            <p class="text-muted">${errorMessage || '加载图表时出现错误，请稍后再试。'}</p>
        </div>
    `;
    
    // 替换图表容器内容
    chartContainer.innerHTML = errorHtml;
}