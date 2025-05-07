/**
 * 波动率图表配置
 */
function getVolatilityChartConfig(timestamps, volaxivity, volatilitySkew) {
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '波动率指数',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    data: volaxivity.map(v => v * 100), // 转换为百分比
                    yAxisID: 'y',
                },
                {
                    label: '波动率偏斜',
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    data: volatilitySkew,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 0) {
                                label += formatNumber(context.raw, 2) + '%';
                            } else {
                                label += formatNumber(context.raw, 3);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '波动率指数 (%)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '波动率偏斜'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
    };
}

/**
 * PCR图表配置
 */
function getPCRChartConfig(timestamps, pcrValues, priceValues) {
    // 找出价格的最小值和最大值，计算合适的比例因子
    const minPrice = Math.min(...priceValues.filter(p => p > 0));
    const maxPrice = Math.max(...priceValues);
    const priceRange = maxPrice - minPrice;
    
    // 调整后的价格值，使其与PCR值在同一个范围内显示
    const scaledPrices = priceValues.map(price => {
        if (price === 0) return null;
        return 0.5 + (price - minPrice) / priceRange;
    });
    
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '看跌/看涨比率',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    data: pcrValues,
                    yAxisID: 'y',
                },
                {
                    label: '价格',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    borderDash: [5, 5],
                    data: priceValues,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 0) {
                                label += formatNumber(context.raw, 2);
                            } else {
                                label += '$' + formatNumber(context.raw, 0);
                            }
                            return label;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: 1,
                            yMax: 1,
                            borderColor: 'rgba(200, 200, 200, 0.5)',
                            borderWidth: 1,
                            borderDash: [6, 6],
                            label: {
                                content: '中性',
                                position: 'end',
                                backgroundColor: 'rgba(200, 200, 200, 0.5)',
                                color: 'white',
                                enabled: true
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
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
                    min: 0,
                    suggestedMax: 2,
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '价格 (USD)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
    };
}

/**
 * 希腊字母图表配置
 */
function getGreeksChartConfig(timestamps, reflexivityValues) {
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '反身性指标',
                    backgroundColor: 'rgba(255, 159, 64, 0.2)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    data: reflexivityValues,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += formatNumber(context.raw, 3);
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    title: {
                        display: true,
                        text: '反身性指标值'
                    },
                    min: 0,
                    suggestedMax: 1,
                }
            }
        }
    };
}

/**
 * 风险等级图表配置
 */
function getRiskLevelChartConfig(timestamps, riskLevels) {
    // 将风险等级文本转换为数值
    const riskLevelValues = riskLevels.map(level => {
        switch (level) {
            case 'low': return 0;
            case 'medium': return 1;
            case 'high': return 2;
            case 'extreme': return 3;
            default: return 1;
        }
    });
    
    return {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: '风险等级',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: function(context) {
                        const index = context.dataIndex;
                        const value = riskLevelValues[index];
                        
                        if (value === 0) return 'rgba(40, 167, 69, 1)';
                        if (value === 1) return 'rgba(255, 193, 7, 1)';
                        if (value === 2) return 'rgba(220, 53, 69, 1)';
                        if (value === 3) return 'rgba(128, 0, 0, 1)';
                        
                        return 'rgba(255, 99, 132, 1)';
                    },
                    pointBorderColor: 'rgba(255, 255, 255, 0.8)',
                    data: riskLevelValues,
                    stepped: true,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let level = '';
                            const value = context.raw;
                            
                            if (value === 0) level = '低';
                            else if (value === 1) level = '中';
                            else if (value === 2) level = '高';
                            else if (value === 3) level = '极高';
                            else level = '未知';
                            
                            return `风险等级: ${level}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    title: {
                        display: true,
                        text: '风险等级'
                    },
                    min: -0.5,
                    max: 3.5,
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            if (value === 0) return '低';
                            if (value === 1) return '中';
                            if (value === 2) return '高';
                            if (value === 3) return '极高';
                            return '';
                        }
                    }
                }
            }
        }
    };
}

/**
 * 交易所PCR比较图表配置
 */
function getExchangePCRComparisonConfig(exchanges, pcrValues) {
    const colors = [
        'rgba(75, 192, 192, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(255, 99, 132, 1)',
        'rgba(153, 102, 255, 1)',
    ];
    
    const backgroundColors = colors.map(color => color.replace('1)', '0.2)'));
    
    return {
        type: 'bar',
        data: {
            labels: exchanges,
            datasets: [
                {
                    label: '看跌/看涨比率',
                    backgroundColor: backgroundColors,
                    borderColor: colors,
                    borderWidth: 1,
                    data: pcrValues,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `PCR: ${formatNumber(context.raw, 2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'PCR值'
                    }
                }
            }
        }
    };
}

/**
 * 成交量分布图表配置
 */
function getVolumeDistributionConfig(callVolume, putVolume) {
    return {
        type: 'doughnut',
        data: {
            labels: ['看涨期权', '看跌期权'],
            datasets: [
                {
                    data: [callVolume, putVolume],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 99, 132, 0.8)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)'
                    ],
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const total = callVolume + putVolume;
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            
                            return `${label}: ${formatNumber(value, 0)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
}

/**
 * 处理图表错误
 */
function handleChartError(container, message) {
    if (!container) return;
    
    container.innerHTML = `
        <div class="d-flex justify-content-center align-items-center h-100">
            <div class="text-center text-muted">
                <i class="fas fa-chart-line fa-3x mb-3"></i>
                <p>${message}</p>
            </div>
        </div>
    `;
}

/**
 * 格式化数字
 */
function formatNumber(number, decimals = 2) {
    if (number === null || number === undefined || isNaN(number)) {
        return '--';
    }
    
    return parseFloat(number).toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    if (!dateString) return '--';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}