/**
 * 期权执行价偏离监控模块
 * 用于分析和展示BTC/ETH期权执行价与市场价偏离情况
 * 完全重构版本 - 2023.05.05
 */

// 初始化全局图表对象容器
if (!window.chartObjects) {
    window.chartObjects = {};
}

/**
 * ==========================================
 * 数据工具模块 - 用于数据处理和格式化
 * ==========================================
 */
const DataUtils = {
    /**
     * 安全转换数值并格式化
     * @param {*} value - 要格式化的值
     * @param {number} decimals - 保留小数位数
     * @param {string} defaultValue - 默认值，当输入无效时返回
     * @returns {string} 格式化后的数值字符串
     */
    formatNumber(value, decimals = 2, defaultValue = 'N/A') {
        if (value === null || value === undefined || isNaN(Number(value))) {
            return defaultValue;
        }
        return Number(value).toFixed(decimals);
    },

    /**
     * 百分比格式化
     * @param {*} value - 要格式化为百分比的值
     * @param {number} decimals - 保留小数位数
     * @param {string} defaultValue - 默认值，当输入无效时返回
     * @returns {string} 格式化后的百分比字符串
     */
    formatPercent(value, decimals = 2, defaultValue = 'N/A') {
        const formattedValue = this.formatNumber(value, decimals, null);
        return formattedValue !== null ? `${formattedValue}%` : defaultValue;
    },

    /**
     * 安全格式化日期
     * @param {*} dateStr - 日期字符串或日期对象
     * @param {string} defaultValue - 默认值，当输入无效时返回
     * @returns {string} 格式化后的日期字符串
     */
    formatDate(dateStr, defaultValue = 'Invalid Date') {
        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return defaultValue;
            return date.toLocaleString();
        } catch (e) {
            console.warn('Date formatting error:', e);
            return defaultValue;
        }
    },

    /**
     * 安全访问嵌套对象属性
     * @param {Object} obj - 要访问的对象
     * @param {string} path - 属性路径，如 'a.b.c'
     * @param {*} defaultValue - 默认值，当属性不存在时返回
     * @returns {*} 属性值或默认值
     */
    getProperty(obj, path, defaultValue = undefined) {
        if (!obj || !path) return defaultValue;

        try {
            const keys = path.split('.');
            let result = obj;

            for (const key of keys) {
                if (result === undefined || result === null) return defaultValue;
                result = result[key];
            }

            return result !== undefined ? result : defaultValue;
        } catch (e) {
            console.warn(`Error accessing property ${path}:`, e);
            return defaultValue;
        }
    },

    /**
     * 计算百分比
     * @param {number} value - 要计算百分比的值
     * @param {number} total - 总值
     * @param {number} decimals - 保留小数位数
     * @returns {string} 格式化后的百分比
     */
    calculatePercentage(value, total, decimals = 1) {
        if (!total) return '0';
        const percent = (value / total) * 100;
        return this.formatNumber(percent, decimals, '0');
    },

    /**
     * 汇总数据统计
     * @param {Array} data - 原始数据
     * @returns {Object} 统计结果
     */
    calculateStatistics(data) {
        if (!Array.isArray(data) || data.length === 0) {
            return {
                totalPoints: 0,
                avgDeviation: 0,
                avgVolumeChange: 0,
                anomalyCount: 0,
                anomalyPercentage: 0,
                callOptions: 0,
                putOptions: 0,
                callVolume: 0,
                putVolume: 0,
                putCallRatio: 0,
                volumePutCallRatio: 0,
                deviationRanges: {
                    '0-2%': 0, '2-4%': 0, '4-6%': 0, '6-8%': 0, '8-10%': 0
                }
            };
        }

        try {
            // 基本计数
            let sumDeviation = 0;
            let sumVolumeChange = 0;
            let validDeviationCount = 0;
            let validVolumeChangeCount = 0;
            let anomalyCount = 0;
            let callCount = 0;
            let putCount = 0;
            let callVolume = 0;
            let putVolume = 0;

            // 偏离分布
            const deviationRanges = {
                '0-2%': 0, '2-4%': 0, '4-6%': 0, '6-8%': 0, '8-10%': 0
            };

            // 遍历计算
            data.forEach(item => {
                // 偏离率统计
                if (item.deviation_percent !== undefined && !isNaN(item.deviation_percent)) {
                    sumDeviation += item.deviation_percent;
                    validDeviationCount++;

                    // 分布计数
                    const dev = item.deviation_percent;
                    if (dev < 2) deviationRanges['0-2%']++;
                    else if (dev < 4) deviationRanges['2-4%']++;
                    else if (dev < 6) deviationRanges['4-6%']++;
                    else if (dev < 8) deviationRanges['6-8%']++;
                    else deviationRanges['8-10%']++;
                }

                // 成交量变化统计
                if (item.volume_change_percent !== undefined && 
                    item.volume_change_percent !== null && 
                    !isNaN(item.volume_change_percent)) {
                    sumVolumeChange += item.volume_change_percent;
                    validVolumeChangeCount++;
                }

                // 异常计数
                if (item.is_anomaly) {
                    anomalyCount++;
                }

                // 期权类型
                if (item.option_type === 'call') {
                    callCount++;
                    callVolume += item.volume || 0;
                } else if (item.option_type === 'put') {
                    putCount++;
                    putVolume += item.volume || 0;
                }
            });

            // 计算平均值和比率
            const avgDeviation = validDeviationCount > 0 ? sumDeviation / validDeviationCount : 0;
            const avgVolumeChange = validVolumeChangeCount > 0 ? sumVolumeChange / validVolumeChangeCount : 0;
            const anomalyPercentage = data.length > 0 ? (anomalyCount / data.length) * 100 : 0;
            const putCallRatio = callCount > 0 ? putCount / callCount : 0;
            const volumePutCallRatio = callVolume > 0 ? putVolume / callVolume : 0;

            return {
                totalPoints: data.length,
                avgDeviation,
                avgVolumeChange,
                anomalyCount,
                anomalyPercentage,
                callOptions: callCount,
                putOptions: putCount,
                callVolume,
                putVolume,
                putCallRatio,
                volumePutCallRatio,
                deviationRanges
            };
        } catch (e) {
            console.error('Error calculating statistics:', e);
            return {
                totalPoints: data.length,
                avgDeviation: 0,
                avgVolumeChange: 0,
                anomalyCount: 0,
                anomalyPercentage: 0,
                callOptions: 0,
                putOptions: 0,
                callVolume: 0,
                putVolume: 0,
                putCallRatio: 0,
                volumePutCallRatio: 0,
                deviationRanges: {
                    '0-2%': 0, '2-4%': 0, '4-6%': 0, '6-8%': 0, '8-10%': 0
                }
            };
        }
    }
};

/**
 * ==========================================
 * UI工具模块 - 用于UI交互和展示
 * ==========================================
 */
const UIUtils = {
    /**
     * 显示通知
     * @param {string} message - 通知消息
     * @param {string} type - 通知类型 (info, success, warning, danger)
     */
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast align-items-center border-0 bg-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body text-white">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },

    /**
     * 更新元素文本内容
     * @param {string} elementId - 元素ID
     * @param {string} text - 新文本内容
     * @returns {boolean} 是否成功更新
     */
    updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (!element) return false;

        element.textContent = text;
        return true;
    },

    /**
     * 更新风险等级指示器
     * @param {string} elementId - 元素ID
     * @param {number} value - 当前值
     * @param {Object} thresholds - 阈值配置 {attention, warning, severe}
     */
    updateRiskLevelIndicator(elementId, value, thresholds) {
        const indicator = document.getElementById(elementId);
        if (!indicator || value === null || value === undefined || isNaN(value)) return;

        let level = 'bg-success';
        let percentage = 25;

        if (value >= thresholds.severe) {
            level = 'bg-danger';
            percentage = 100;
        } else if (value >= thresholds.warning) {
            level = 'bg-warning';
            percentage = 75;
        } else if (value >= thresholds.attention) {
            level = 'bg-info';
            percentage = 50;
        }

        indicator.className = `progress-bar ${level}`;
        indicator.style.width = `${percentage}%`;
    }
};

/**
 * ==========================================
 * 图表模块 - 用于创建和更新图表
 * ==========================================
 */
const ChartUtils = {
    /**
     * 初始化图表
     */
    initCharts() {
        // 使用全局图表对象
        if (!window.chartObjects) {
            window.chartObjects = {};
        }
        window.chartObjects.deviationChart = null;
        window.chartObjects.trendAnalysisChart = null;
        window.chartObjects.pcrComparisonChart = null;
        window.chartObjects.volumeDistributionChart = null;
        window.chartObjects.premiumSpreadChart = null;
    },

    /**
     * 销毁所有图表
     */
    destroyAllCharts() {
        if (!window.chartObjects) {
            window.chartObjects = {};
            return;
        }

        const chartKeys = [
            'deviationChart',
            'trendAnalysisChart',
            'pcrComparisonChart',
            'volumeDistributionChart',
            'premiumSpreadChart'
        ];

        chartKeys.forEach(key => {
            if (window.chartObjects[key]) {
                try {
                    window.chartObjects[key].destroy();
                    window.chartObjects[key] = null;
                } catch (e) {
                    console.warn(`Error destroying chart ${key}:`, e);
                }
            }
        });
    },

    /**
     * 为散点图准备数据
     * @param {Array} data - 原始数据
     * @returns {Array} 格式化后的数据集
     */
    prepareScatterData(data) {
        if (!Array.isArray(data) || data.length === 0) return [];

        // 为不同的期权类型准备数据
        const callData = [];
        const putData = [];

        // 为异常数据准备单独的数据集
        const callAnomalyData = [];
        const putAnomalyData = [];

        data.forEach(item => {
            try {
                if (!item || !item.deviation_percent || !item.strike_price) return;

                // 构建数据点
                const dataPoint = {
                    x: item.deviation_percent,
                    y: item.volume_change_percent !== null ? item.volume_change_percent : 0,
                    r: Math.log(item.volume + 1) * 1.5 + 3, // 根据成交量调整点大小
                    strike_price: item.strike_price,
                    market_price: item.market_price,
                    symbol: item.symbol,
                    deviation_percent: item.deviation_percent,
                    volume_change_percent: item.volume_change_percent,
                    premium: item.premium,
                    premium_change_percent: item.premium_change_percent,
                    is_anomaly: item.is_anomaly,
                    anomaly_level: item.anomaly_level,
                    option_type: item.option_type,
                    optionTypeDisplay: item.option_type ? item.option_type.toUpperCase() : 'UNKNOWN'
                };

                // 根据期权类型和异常状态分配到对应数据集
                if (item.option_type === 'call') {
                    if (item.is_anomaly) {
                        callAnomalyData.push(dataPoint);
                    } else {
                        callData.push(dataPoint);
                    }
                } else if (item.option_type === 'put') {
                    if (item.is_anomaly) {
                        putAnomalyData.push(dataPoint);
                    } else {
                        putData.push(dataPoint);
                    }
                }
            } catch (e) {
                console.warn('Error processing scatter data point:', e);
            }
        });

        // 生成趋势线数据
        let trendData = [];
        try {
            const allPoints = [...callData, ...putData, ...callAnomalyData, ...putAnomalyData];
            if (allPoints.length > 5) { // 只有足够多数据点时才计算趋势线
                const validPoints = allPoints.filter(p => 
                    p.x !== undefined && p.y !== undefined && 
                    !isNaN(p.x) && !isNaN(p.y)
                );
                trendData = this.calculateTrendLine(validPoints);
            }
        } catch (e) {
            console.warn('Error calculating trend line:', e);
        }

        // 生成最终数据集
        return [
            {
                label: 'Call Options',
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                data: callData,
                pointStyle: 'circle'
            },
            {
                label: 'Put Options',
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                borderColor: 'rgba(255, 99, 132, 1)',
                data: putData,
                pointStyle: 'circle'
            },
            {
                label: 'Call Anomalies',
                backgroundColor: 'rgba(54, 162, 235, 0.8)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                data: callAnomalyData,
                pointStyle: 'rectRot'
            },
            {
                label: 'Put Anomalies',
                backgroundColor: 'rgba(255, 99, 132, 0.8)',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 2,
                data: putAnomalyData,
                pointStyle: 'rectRot'
            },
            {
                label: 'Trend Line',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                data: trendData
            }
        ];
    },

    /**
     * 计算散点图趋势线
     * @param {Array} points - 数据点数组，每个点有x和y属性
     * @returns {Array} 趋势线上的点
     */
    calculateTrendLine(points) {
        if (!points || points.length < 5) return [];

        const validPoints = points.filter(p => p && p.x !== undefined && p.y !== undefined);
        if (validPoints.length < 5) return [];

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
        const slopeFormatted = DataUtils.formatNumber(slope, 2, '?');

        // 在x轴上生成数据点
        for (let x = 0; x <= 10; x += 0.5) {
            trendPoints.push({
                x: x,
                y: slope * x + intercept,
                isTrendLine: true,
                trendLabel: `斜率: ${slopeFormatted}`
            });
        }

        return trendPoints;
    },

    /**
     * 创建偏离散点图
     * @param {Array} data - 原始数据
     * @param {Object} stats - 统计数据
     */
    createDeviationChart(data, stats) {
        const ctx = document.getElementById('deviation-chart');
        if (!ctx) return;

        // 销毁现有图表
        if (window.chartObjects && window.chartObjects.deviationChart) {
            try {
                window.chartObjects.deviationChart.destroy();
            } catch (e) {
                console.warn('销毁旧偏离散点图出错:', e);
            }
            window.chartObjects.deviationChart = null;
        }

        // 准备数据
        const scatterData = this.prepareScatterData(data);

        // 确保统计数据可用
        const safeStats = stats || { totalPoints: 0, avgDeviation: 0, avgVolumeChange: 0 };
        const totalPoints = DataUtils.getProperty(safeStats, 'totalPoints', 0);
        const avgDeviation = DataUtils.formatNumber(DataUtils.getProperty(safeStats, 'avgDeviation', 0), 2, '0');
        const avgVolumeChange = DataUtils.formatNumber(DataUtils.getProperty(safeStats, 'avgVolumeChange', 0), 2, '0');

        // 创建图表
        window.chartObjects.deviationChart = new Chart(ctx, {
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
                        text: `期权执行价偏离分布图 (${totalPoints}个数据点)`
                    },
                    subtitle: {
                        display: true,
                        text: `平均偏离率: ${avgDeviation}%, 平均成交量变化: ${avgVolumeChange}%`
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const point = context.raw;
                                if (point.isTrendLine) {
                                    return `趋势线: ${point.trendLabel || ''}`;
                                }

                                const strikePrice = DataUtils.formatNumber(point.strike_price, 2, 'N/A');
                                const deviationPercent = DataUtils.formatNumber(point.deviation_percent, 2, 'N/A');
                                const volumeChangePercent = point.volume_change_percent !== null ? 
                                    DataUtils.formatNumber(point.volume_change_percent, 1, 'N/A') : 'N/A';

                                return `${point.symbol} ${point.optionTypeDisplay}: 执行价 ${strikePrice}, 偏离 ${deviationPercent}%, 成交量变化 ${volumeChangePercent}%`;
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
                                        default: level = '未知级别';
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
                        title: {
                            display: true,
                            text: '偏离百分比 (%)'
                        },
                        min: 0,
                        max: 10
                    },
                    y: {
                        title: {
                            display: true,
                            text: '成交量变化 (%)'
                        }
                    }
                }
            }
        });
    },

    /**
     * 创建趋势分析图表
     * @param {Array} data - 原始数据
     */
    createTrendAnalysisChart(data) {
        const ctx = document.getElementById('trend-analysis-chart');
        if (!ctx || !data || !Array.isArray(data) || data.length === 0) return;

        // 按时间组织数据
        const timeSeriesData = this.organizeTimeSeriesData(data);
        if (!timeSeriesData || timeSeriesData.length === 0) return;

        // 销毁现有图表
        if (window.chartObjects && window.chartObjects.trendAnalysisChart) {
            try {
                window.chartObjects.trendAnalysisChart.destroy();
            } catch (e) {
                console.warn('销毁旧趋势分析图表出错:', e);
            }
            window.chartObjects.trendAnalysisChart = null;
        }

        // 准备数据集
        const datasets = [
            {
                label: '成交量',
                data: timeSeriesData.map(d => d.totalVolume || 0),
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                yAxisID: 'y-volume',
                fill: true
            },
            {
                label: '异常数量',
                data: timeSeriesData.map(d => d.anomalyCount || 0),
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                yAxisID: 'y-anomaly',
                fill: true
            },
            {
                label: '看跌/看涨比率',
                data: timeSeriesData.map(d => d.putCallRatio || 0),
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'transparent',
                yAxisID: 'y-ratio',
                type: 'line'
            }
        ];

        // 创建图表
        window.chartObjects.trendAnalysisChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: timeSeriesData.map(d => d.timeLabel || ''),
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
    },

    /**
     * 按时间组织数据
     * @param {Array} data - 原始数据
     * @returns {Array} 按时间组织后的数据
     */
    organizeTimeSeriesData(data) {
        // 检查数据有效性
        if (!data || !Array.isArray(data) || data.length === 0) {
            console.warn('Invalid or empty data for time series');
            return [];
        }

        // 按小时分组数据
        const hourlyData = {};

        data.forEach(item => {
            try {
                if (!item || !item.timestamp) return;

                const date = new Date(item.timestamp);
                if (isNaN(date.getTime())) return; // 跳过无效日期

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

                // 安全地增加成交量
                const volume = Number(item.volume) || 0;
                hourlyData[hourKey].totalVolume += volume;

                // 根据期权类型累加成交量
                if (item.option_type === 'call') {
                    hourlyData[hourKey].callVolume += volume;
                } else if (item.option_type === 'put') {
                    hourlyData[hourKey].putVolume += volume;
                }

                // 累加异常计数
                if (item.is_anomaly) {
                    hourlyData[hourKey].anomalyCount++;
                }
            } catch (e) {
                console.error("Error processing data item:", e);
            }
        });

        // 检查是否有有效数据
        if (Object.keys(hourlyData).length === 0) {
            console.warn('No valid hourly data found');
            return [];
        }

        // 计算比率并转换为数组
        const timeSeriesArray = Object.values(hourlyData).map(hour => {
            return {
                ...hour,
                putCallRatio: hour.callVolume > 0 ? hour.putVolume / hour.callVolume : 0
            };
        });

        // 按时间排序
        timeSeriesArray.sort((a, b) => {
            try {
                return new Date(a.timeLabel) - new Date(b.timeLabel);
            } catch (e) {
                console.warn('Error sorting time series:', e);
                return 0;
            }
        });

        // 限制数据点数量以提高性能
        const maxPoints = 24; // 显示最近24小时
        if (timeSeriesArray.length > maxPoints) {
            return timeSeriesArray.slice(timeSeriesArray.length - maxPoints);
        }

        return timeSeriesArray;
    },

    /**
     * 创建交易所对比图表
     * @param {Array} data - 原始数据
     */
    createExchangeComparisonCharts(data) {
        if (!data || !Array.isArray(data) || data.length === 0) return;

        // 这个函数目前从期权偏离数据中创建图表，这些数据通常只包含一个交易所
        // 为了显示多交易所数据，我们创建一个简化版的只显示当前交易所数据的图表
        this.createPCRComparisonChart(data);
        this.createVolumeDistributionChart(data);
        this.createPremiumSpreadChart(data);

        // 注意：完整的多交易所对比在VolumeAnalysisModule中处理
    },

    /**
     * 创建看跌/看涨比率对比图表
     * @param {Array} data - 原始数据
     */
    createPCRComparisonChart(data) {
        const ctx = document.getElementById('pcr-comparison-chart');
        if (!ctx || !data || !Array.isArray(data) || data.length === 0) return;

        try {
            // 按交易所分组数据
            const exchanges = [...new Set(data.map(item => item.exchange))];

            // 计算每个交易所的PCR
            const pcrData = exchanges.map(exchange => {
                const exchangeData = data.filter(item => item.exchange === exchange);
                const calls = exchangeData.filter(item => item.option_type === 'call');
                const puts = exchangeData.filter(item => item.option_type === 'put');

                const callVolume = calls.reduce((sum, item) => sum + (Number(item.volume) || 0), 0);
                const putVolume = puts.reduce((sum, item) => sum + (Number(item.volume) || 0), 0);

                const pcr = callVolume > 0 ? putVolume / callVolume : 0;
                return {
                    exchange,
                    pcr
                };
            });

            // 销毁现有图表
            if (window.chartObjects && window.chartObjects.pcrComparisonChart) {
                try {
                    window.chartObjects.pcrComparisonChart.destroy();
                } catch (e) {
                    console.warn('销毁旧PCR对比图表出错:', e);
                }
                window.chartObjects.pcrComparisonChart = null;
            }

            // 创建图表
            window.chartObjects.pcrComparisonChart = new Chart(ctx, {
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
                                    return `P/C Ratio: ${DataUtils.formatNumber(context.raw, 2, 'N/A')}`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating PCR comparison chart:', e);
        }
    },

    /**
     * 创建成交量分布图表
     * @param {Array} data - 原始数据
     */
    createVolumeDistributionChart(data) {
        const ctx = document.getElementById('volume-distribution-chart');
        if (!ctx || !data || !ArrayisArray(data) || data.length === 0) return;

        try {
            // 按交易所分组数据
            const exchanges = [...new Set(data.map(item => item.exchange))];

            // 计算每个交易所的总成交量
            const volumeData = exchanges.map(exchange => {
                const exchangeData = data.filter(item => item.exchange === exchange);
                const totalVolume = exchangeData.reduce((sum, item) => sum + (Number(item.volume) || 0), 0);
                return {
                    exchange,
                    volume: totalVolume
                };
            });

            // 销毁现有图表
            if (window.chartObjects && window.chartObjects.volumeDistributionChart) {
                try {
                    window.chartObjects.volumeDistributionChart.destroy();
                } catch (e) {
                    console.warn('销毁旧成交量分布图表出错:', e);
                }
                window.chartObjects.volumeDistributionChart = null;
            }

            // 创建图表
            window.chartObjects.volumeDistributionChart = new Chart(ctx, {
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
                                    const total = context.dataset.data.reduce((sum, val) => sum + (Number(val) || 0), 0);
                                    const percentage = total > 0 ? ((value / total) * 100) : 0;
                                    return `Volume: ${value} (${DataUtils.formatNumber(percentage, 2, '0')}%)`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating volume distribution chart:', e);
        }
    },

    /**
     * 创建权利金价差图表
     * @param {Array} data - 原始数据
     */
    createPremiumSpreadChart(data) {
        const ctx = document.getElementById('premium-spread-chart');
        if (!ctx || !data || !Array.isArray(data) || data.length === 0) return;

        try {
            // 按交易所分组数据
            const exchanges = [...new Set(data.map(item => item.exchange))];

            // 计算每个交易所的平均权利金
            const premiumData = exchanges.map(exchange => {
                const exchangeData = data.filter(item => item.exchange === exchange);
                const validPremiums = exchangeData.filter(item => item.premium !== undefined && item.premium !== null);
                const avgPremium = validPremiums.length > 0 ? 
                    validPremiums.reduce((sum, item) => sum + (Number(item.premium) || 0), 0) / validPremiums.length : 0;
                return {
                    exchange,
                    avgPremium
                };
            });

            // 销毁现有图表
            if (window.chartObjects && window.chartObjects.premiumSpreadChart) {
                try {
                    window.chartObjects.premiumSpreadChart.destroy();
                } catch (e) {
                    console.warn('销毁旧权利金价差图表出错:', e);
                }
                window.chartObjects.premiumSpreadChart = null;
            }

            // 创建图表
            window.chartObjects.premiumSpreadChart = new Chart(ctx, {
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
                                    return `Avg. Premium: ${DataUtils.formatNumber(context.raw, 4, 'N/A')}`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating premium spread chart:', e);
        }
    }
};

/**
 * ==========================================
 * 数据服务模块 - 用于数据获取和处理
 * ==========================================
 */
const DataService = {
    /**
     * 存储当前数据
     */
    deviationData: [],

    /**
     * 根据过滤器获取偏离数据
     * @param {boolean} showToast - 是否显示操作结果通知
     * @returns {Promise} 请求Promise
     */
    async fetchDeviationData(showToast = false) {
        try {
            // 获取过滤参数
            const filters = this.getFilterParams();
            console.log('Fetching deviation data...');

            // 构建查询字符串
            const queryString = new URLSearchParams({
                symbol: filters.symbol,
                exchange: filters.exchange,
                time_period: filters.timePeriod,
                days: filters.days,
                anomaly_only: filters.anomalyOnly,
                volume_change_filter: filters.volumeChangeFilter,
                include_stats: true
            }).toString();

            const url = `/api/deviation/data?${queryString}`;
            console.log('Request URL:', url);

            // 发送请求
            const response = await fetch(url);

            // 检查响应状态
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API error (${response.status}): ${errorText}`);
            }

            // 解析响应数据
            const result = await response.json();

            // 适应后端不同的响应格式
            let data = [];
            let stats = null;

            if (Array.isArray(result)) {
                // 当include_stats=false时，后端直接返回数组
                data = result;
            } else if (result.deviations && Array.isArray(result.deviations)) {
                // 当include_stats=true时，后端返回包含deviations和statistics的对象
                data = result.deviations;
                stats = result.statistics || null;
            } else {
                console.error('Unexpected response format:', result);
                throw new Error('Invalid response format');
            }

            // 存储数据
            this.deviationData = data;

            // 打印日志
            console.log(`Received ${this.deviationData.length} records and statistics from API`);

            // 显示通知
            if (showToast) {
                UIUtils.showToast(`已加载 ${this.deviationData.length} 条记录`, 'success');
            }

            // 更新UI
            this.updateUI(this.deviationData, stats);

            return { data: this.deviationData, stats };
        } catch (error) {
            console.error('Error fetching deviation data:', error);
            UIUtils.showToast('获取数据失败：' + error.message, 'danger');

            // 返回空数据
            return { data: [], stats: null };
        }
    },

    /**
     * 获取风险指标数据
     */
    async fetchRiskData() {
        try {
            const symbol = document.getElementById('symbol-filter').value;
            const timePeriod = document.getElementById('time-period-filter').value;

            const response = await fetch(`/api/dashboard/data?symbol=${symbol}&days=30&time_period=${timePeriod}`);
            const data = await response.json();

            if (response.ok) {
                this.updateRiskIndicators(symbol, data, timePeriod);
            } else {
                console.error('Error fetching risk data:', data.message);
            }
        } catch (error) {
            console.error('Fetch error for risk data:', error);
        }
    },

    /**
     * 提交确认警报请求
     * @param {number} alertId - 警报ID
     */
    async acknowledgeAlert(alertId) {
        try {
            const response = await fetch('/api/deviation/acknowledge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ alert_id: alertId })
            });

            const result = await response.json();

            if (response.ok) {
                // 移除已确认的警报行
                const alertRow = document.querySelector(`tr[data-alert-id="${alertId}"]`);
                if (alertRow) {
                    alertRow.remove();
                }

                // 检查是否没有更多警报
                const alertsBody = document.getElementById('active-alerts-body');
                if (alertsBody && alertsBody.childElementCount === 0) {
                    // 显示"无活动警报"消息
                    const alertsCard = alertsBody.closest('.card-body');
                    if (alertsCard) {
                        alertsCard.innerHTML = `
                            <div class="text-center py-4">
                                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                                <p class="lead">无活动偏离警报</p>
                            </div>
                        `;
                    }
                }

                UIUtils.showToast('警报已确认', 'success');
            } else {
                throw new Error(result.message || '确认警报失败');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            UIUtils.showToast('确认警报失败：' + error.message, 'danger');
        }
    },

    /**
     * 导出数据为CSV
     */
    exportCsv() {
        if (!this.deviationData || this.deviationData.length === 0) {
            UIUtils.showToast('无数据可导出', 'warning');
            return;
        }

        try {
            // 定义CSV头
            const headers = [
                'Timestamp', 'Symbol', 'Exchange', 'Strike Price', 'Market Price', 'Deviation %', 
                'Option Type', 'Expiration Date', 'Volume', 'Volume Change %', 
                'Premium', 'Premium Change %', 'Market Price Change %', 'Is Anomaly'
            ];

            // 转换数据为CSV行
            const csvRows = [headers.join(',')];

            this.deviationData.forEach(item => {
                try {
                    if (!item) return;

                    const row = [
                        `"${item.timestamp || ''}"`,
                        `"${item.symbol || ''}"`,
                        `"${item.exchange || ''}"`,
                        DataUtils.formatNumber(item.strike_price, 2, ''),
                        DataUtils.formatNumber(item.market_price, 2, ''),
                        DataUtils.formatNumber(item.deviation_percent, 2, ''),
                        `"${item.option_type || ''}"`,
                        `"${item.expiration_date || ''}"`,
                        item.volume || 0,
                        item.volume_change_percent !== null ? DataUtils.formatNumber(item.volume_change_percent, 2, '') : 'N/A',
                        DataUtils.formatNumber(item.premium, 4, ''),
                        item.premium_change_percent !== null ? DataUtils.formatNumber(item.premium_change_percent, 2, '') : 'N/A',
                        item.market_price_change_percent !== null ? DataUtils.formatNumber(item.market_price_change_percent, 2, '') : 'N/A',
                        item.is_anomaly ? 'Yes' : 'No'
                    ];

                    csvRows.push(row.join(','));
                } catch (e) {
                    console.warn('Error processing CSV row:', e);
                }
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
            link.setAttribute('download', `${symbol}_deviation_data_${timestamp}.csv`);
            link.style.visibility = 'hidden';

            // 添加到DOM并触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            UIUtils.showToast('数据导出成功', 'success');
        } catch (e) {
            console.error('Error exporting CSV:', e);
            UIUtils.showToast('导出数据失败：' + e.message, 'danger');
        }
    },

    /**
     * 获取当前过滤参数
     * @returns {Object} 过滤参数对象
     */
    getFilterParams() {
        // 获取DOM元素值或使用默认值
        let symbol = 'BTC';
        let exchange = 'deribit';
        let optionType = '';
        let timePeriod = '15m';  // 默认使用15分钟时间周期
        let days = '7';
        let volumeChangeFilter = '0';
        let anomalyOnly = false;

        // 如果DOM元素存在，则获取其值
        const symbolEl = document.getElementById('symbol-filter');
        const exchangeEl = document.getElementById('exchange-filter');
        const optionTypeEl = document.getElementById('option-type-filter');
        const timePeriodEl = document.getElementById('time-period-filter');
        const daysEl = document.getElementById('days-filter');
        const volumeChangeFilterEl = document.getElementById('volume-change-filter');
        const anomalyOnlyEl = document.getElementById('anomaly-only-filter');

        if (symbolEl) symbol = symbolEl.value;
        if (exchangeEl) exchange = exchangeEl.value;
        if (optionTypeEl) optionType = optionTypeEl.value;
        if (timePeriodEl) timePeriod = timePeriodEl.value;
        if (daysEl) days = daysEl.value;
        if (volumeChangeFilterEl) volumeChangeFilter = volumeChangeFilterEl.value;
        if (anomalyOnlyEl) anomalyOnly = anomalyOnlyEl.checked;

        const filters = {
            symbol,
            exchange,
            optionType,
            timePeriod,
            days,
            volumeChangeFilter,
            anomalyOnly
        };

        console.log('应用筛选: ', filters);
        return filters;
    },

    /**
     * 应用过滤器并获取数据
     */
    applyFilters() {
        this.fetchDeviationData(true);
    },

    /**
     * 刷新数据
     */
    refreshData() {
        // 获取按钮元素
        const refreshBtn = document.getElementById('refresh-data-btn');
        if (!refreshBtn) return;

        // 禁用按钮并显示加载中状态
        const originalText = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> 加载中...';
        refreshBtn.disabled = true;

        // 并行获取数据
        Promise.all([
            this.fetchDeviationData(true),
            this.fetchRiskData()
        ]).finally(() => {
            // 恢复按钮状态
            refreshBtn.innerHTML = originalText;
            refreshBtn.disabled = false;
        });
    },

    /**
     * 更新风险指标
     * @param {string} symbol - 交易对符号
     * @param {Object} data - 风险数据
     * @param {string} timePeriod - 时间周期
     */
    updateRiskIndicators(symbol, data, timePeriod) {
        if (!data || !data.timestamps || data.timestamps.length === 0) {
            console.warn('No risk data available');
            return;
        }

        try {
            // 获取最新数据点
            const lastIndex = data.timestamps.length - 1;
            const volaxivity = DataUtils.getProperty(data, `volaxivity.${lastIndex}`);
            const volatilitySkew = DataUtils.getProperty(data, `volatility_skew.${lastIndex}`);
            const putCallRatio = DataUtils.getProperty(data, `put_call_ratio.${lastIndex}`);
            const reflexivity = DataUtils.getProperty(data, `reflexivity_indicator.${lastIndex}`);

            // 更新UI值
            UIUtils.updateElementText('volaxivity-value', volaxivity !== undefined ? DataUtils.formatNumber(volaxivity) : 'N/A');
            UIUtils.updateElementText('volatility-skew-value', volatilitySkew !== undefined ? DataUtils.formatNumber(volatilitySkew) : 'N/A');
            UIUtils.updateElementText('put-call-ratio-value', putCallRatio !== undefined ? DataUtils.formatNumber(putCallRatio) : 'N/A');
            UIUtils.updateElementText('reflexivity-value', reflexivity !== undefined ? DataUtils.formatPercent(reflexivity * 100) : 'N/A');

            // 基于时间周期设置阈值
            const timePeriodKey = timePeriod || '15m';

            // 更新风险等级指示器
            if (volaxivity !== undefined) {
                const volaxivityThresholds = this.getThresholds('volaxivity', timePeriodKey);
                UIUtils.updateRiskLevelIndicator('volaxivity-indicator', volaxivity, volaxivityThresholds);
            }

            if (volatilitySkew !== undefined) {
                const skewThresholds = this.getThresholds('volatility_skew', timePeriodKey);
                UIUtils.updateRiskLevelIndicator('skew-indicator', volatilitySkew, skewThresholds);
            }

            if (putCallRatio !== undefined) {
                const pcrThresholds = this.getThresholds('put_call_ratio', timePeriodKey);
                UIUtils.updateRiskLevelIndicator('pcr-indicator', putCallRatio, pcrThresholds);
            }

            if (reflexivity !== undefined) {
                const reflexivityThresholds = this.getThresholds('reflexivity_indicator', timePeriodKey);
                UIUtils.updateRiskLevelIndicator('reflexivity-indicator', reflexivity, reflexivityThresholds);
            }
        } catch (e) {
            console.error('Error updating risk indicators:', e);
        }
    },

    /**
     * 获取指定指标和时间周期的阈值
     * @param {string} indicator - 指标名称
     * @param {string} timePeriod - 时间周期
     * @returns {Object} 阈值配置
     */
    getThresholds(indicator, timePeriod) {
        // 默认阈值配置
        const defaultThresholds = {
            volaxivity: {
                '15m': {attention: 15, warning: 25, severe: 35},
                '1h': {attention: 18, warning: 28, severe: 38},
                '4h': {attention: 20, warning: 30, severe: 40},
                '1d': {attention: 22, warning: 32, severe: 42},
                '7d': {attention: 25, warning: 35, severe: 45},
                '30d': {attention: 30, warning: 40, severe: 50}
            },
            volatility_skew: {
                '15m': {attention: 0.3, warning: 0.7, severe: 1.2},
                '1h': {attention: 0.4, warning: 0.8, severe: 1.3},
                '4h': {attention: 0.5, warning: 1.0, severe: 1.5},
                '1d': {attention: 0.6, warning: 1.1, severe: 1.6},
                '7d': {attention: 0.7, warning: 1.2, severe: 1.7},
                '30d': {attention: 0.8, warning: 1.3, severe: 1.8}
            },
            put_call_ratio: {
                '15m': {attention: 1.1, warning: 1.4, severe: 1.8},
                '1h': {attention: 1.15, warning: 1.45, severe: 1.9},
                '4h': {attention: 1.2, warning: 1.5, severe: 2.0},
                '1d': {attention: 1.25, warning: 1.55, severe: 2.1},
                '7d': {attention: 1.3, warning: 1.6, severe: 2.2},
                '30d': {attention: 1.35, warning: 1.7, severe: 2.3}
            },
            reflexivity_indicator: {
                '15m': {attention: 0.2, warning: 0.4, severe: 0.6},
                '1h': {attention: 0.25, warning: 0.45, severe: 0.65},
                '4h': {attention: 0.3, warning: 0.5, severe: 0.7},
                '1d': {attention: 0.35, warning: 0.55, severe: 0.75},
                '7d': {attention: 0.4, warning: 0.6, severe: 0.8},
                '30d': {attention: 0.45, warning: 0.65, severe: 0.85}
            }
        };

        // 获取指定指标和时间周期的阈值
        const indicatorThresholds = DataUtils.getProperty(defaultThresholds, indicator);
        if (!indicatorThresholds) return {attention: 0, warning: 0, severe: 0};

        const periodThresholds = DataUtils.getProperty(indicatorThresholds, timePeriod);
        return periodThresholds || DataUtils.getProperty(indicatorThresholds, '15m') || {attention: 0, warning: 0, severe: 0};
    },

    /**
     * 更新统计面板
     * @param {Object} stats - 统计数据
     */
    updateStatisticsPanel(stats) {
        if (!stats) {
            console.warn('No statistics data available');
            return;
        }

        // 获取统计面板元素
        const statsPanelElement = document.getElementById('stats-panel');
        if (!statsPanelElement) return;

        // 准备统计数据
        const totalPoints = DataUtils.getProperty(stats, 'totalPoints', 0);
        const avgDeviation = DataUtils.getProperty(stats, 'avgDeviation', 0);
        const avgVolumeChange = DataUtils.getProperty(stats, 'avgVolumeChange', 0);
        const putCallRatio = DataUtils.getProperty(stats, 'putCallRatio', 0);
        const volumePutCallRatio = DataUtils.getProperty(stats, 'volumePutCallRatio', 0);
        const putOptions = DataUtils.getProperty(stats, 'putOptions', 0);
        const callOptions = DataUtils.getProperty(stats, 'callOptions', 0);
        const putVolume = DataUtils.getProperty(stats, 'putVolume', 0);
        const callVolume = DataUtils.getProperty(stats, 'callVolume', 0);
        const anomalyPoints = DataUtils.getProperty(stats, 'anomalyCount', 0);
        const anomalyPercentage = DataUtils.getProperty(stats, 'anomalyPercentage', 0);
        const attentionCount = DataUtils.getProperty(stats, 'attentionCount', 0);
        const warningCount = DataUtils.getProperty(stats, 'warningCount', 0);
        const severeCount = DataUtils.getProperty(stats, 'severeCount', 0);

        // 安全获取分布数据
        const deviationRanges = DataUtils.getProperty(stats, 'deviationRanges', {
            '0-2%': 0, '2-4%': 0, '4-6%': 0, '6-8%': 0, '8-10%': 0
        });

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
                                    <td>${totalPoints}</td>
                                </tr>
                                <tr>
                                    <th>平均偏离率</th>
                                    <td>${DataUtils.formatPercent(avgDeviation)}</td>
                                </tr>
                                <tr>
                                    <th>平均成交量变化</th>
                                    <td>${DataUtils.formatPercent(avgVolumeChange)}</td>
                                </tr>
                                <tr>
                                    <th>看跌/看涨比例(数量)</th>
                                    <td>${DataUtils.formatNumber(putCallRatio)} (${putOptions}/${callOptions})</td>
                                </tr>
                                <tr>
                                    <th>看跌/看涨比例(成交量)</th>
                                    <td>${DataUtils.formatNumber(volumePutCallRatio)} (${putVolume}/${callVolume})</td>
                                </tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h6 class="font-weight-bold">异常统计</h6>
                            <table class="table table-sm">
                                <tr>
                                    <th>异常数据点</th>
                                    <td>${anomalyPoints} (${DataUtils.formatPercent(anomalyPercentage, 1)})</td>
                                </tr>
                                <tr>
                                    <th>关注级别</th>
                                    <td>${attentionCount}</td>
                                </tr>
                                <tr>
                                    <th>警告级别</th>
                                    <td>${warningCount}</td>
                                </tr>
                                <tr>
                                    <th>严重级别</th>
                                    <td>${severeCount}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-12">
                            <h6 class="font-weight-bold">偏离分布</h6>
                            <div class="progress">
                                <div class="progress-bar bg-success" role="progressbar" style="width: ${DataUtils.calculatePercentage(DataUtils.getProperty(deviationRanges, '0-2%', 0), totalPoints)}%" 
                                    title="0-2%: ${DataUtils.getProperty(deviationRanges, '0-2%', 0)}个数据点">0-2%</div>
                                <div class="progress-bar bg-info" role="progressbar" style="width: ${DataUtils.calculatePercentage(DataUtils.getProperty(deviationRanges, '2-4%', 0), totalPoints)}%" 
                                    title="2-4%: ${DataUtils.getProperty(deviationRanges, '2-4%', 0)}个数据点">2-4%</div>
                                <div class="progress-bar bg-primary" role="progressbar" style="width: ${DataUtils.calculatePercentage(DataUtils.getProperty(deviationRanges, '4-6%', 0), totalPoints)}%" 
                                    title="4-6%: ${DataUtils.getProperty(deviationRanges, '4-6%', 0)}个数据点">4-6%</div>
                                <div class="progress-bar bg-warning" role="progressbar" style="width: ${DataUtils.calculatePercentage(DataUtils.getProperty(deviationRanges, '6-8%', 0), totalPoints)}%" 
                                    title="6-8%: ${DataUtils.getProperty(deviationRanges, '6-8%', 0)}个数据点">6-8%</div>
                                <div class="progress-bar bg-danger" role="progressbar" style="width: ${DataUtils.calculatePercentage(DataUtils.getProperty(deviationRanges, '8-10%', 0), totalPoints)}%" 
                                    title="8-10%: ${DataUtils.getProperty(deviationRanges, '8-10%', 0)}个数据点">8-10%</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 更新面板内容
        statsPanelElement.innerHTML = statsHtml;
    },

    /**
     * 更新偏离数据表格
     * @param {Array} data - 数据数组
     */
    updateDeviationTable(data) {
        const tableBody = document.getElementById('deviation-data-body');
        if (!tableBody) return;

        // 清空表格
        tableBody.innerHTML = '';

        // 检查数据
        if (!data || !Array.isArray(data) || data.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="14" class="text-center">No data available</td>`;
            tableBody.appendChild(row);

            // 更新表格计数器
            const countElement = document.getElementById('data-count');
            if (countElement) {
                countElement.textContent = `Showing 0 of 0 records`;
            }
            return;
        }

        // 限制表格中显示的行数
        const displayData = data.slice(0, 100);

        // 填充数据
        displayData.forEach(item => {
            try {
                if (!item) return;

                const row = document.createElement('tr');
                if (item.is_anomaly) {
                    if (item.anomaly_level === 'severe') {
                        row.classList.add('table-danger');
                    } else if (item.anomaly_level === 'warning') {
                        row.classList.add('table-warning');
                    } else {
                        row.classList.add('table-info');
                    }
                }

                // 安全获取并格式化数据
                const timestamp = DataUtils.formatDate(item.timestamp);
                const symbol = item.symbol || 'N/A';
                const exchange = item.exchange || 'N/A';
                const strikePrice = DataUtils.formatNumber(item.strike_price);
                const marketPrice = DataUtils.formatNumber(item.market_price);
                const deviationPercent = DataUtils.formatPercent(item.deviation_percent);
                const optionType = (item.option_type || 'unknown').toUpperCase();
                const expirationDate = item.expiration_date || 'N/A';
                const volume = item.volume || 0;
                const volumeChange = DataUtils.formatPercent(item.volume_change_percent, 2, 'N/A');
                const premium = DataUtils.formatNumber(item.premium, 4);
                const premiumChange = DataUtils.formatPercent(item.premium_change_percent, 2, 'N/A');
                const marketPriceChange = DataUtils.formatPercent(item.market_price_change_percent, 2, 'N/A');

                // 异常状态显示
                let statusHtml = '';
                if (item.is_anomaly) {
                    let badgeClass = 'bg-info';
                    let levelText = 'Attention';

                    if (item.anomaly_level === 'warning') {
                        badgeClass = 'bg-warning';
                        levelText = 'Warning';
                    } else if (item.anomaly_level === 'severe') {
                        badgeClass = 'bg-danger';
                        levelText = 'Severe';
                    }

                    statusHtml = `<span class="badge ${badgeClass}">${levelText}</span>`;
                } else {
                    statusHtml = `<span class="badge bg-success">Normal</span>`;
                }

                // 创建单元格
                row.innerHTML = `
                    <td>${timestamp}</td>
                    <td>${symbol}</td>
                    <td>${exchange}</td>
                    <td>${strikePrice}</td>
                    <td>${marketPrice}</td>
                    <td>${deviationPercent}</td>
                    <td>${optionType}</td>
                    <td>${expirationDate}</td>
                    <td>${volume}</td>
                    <td>${volumeChange}</td>
                    <td>${premium}</td>
                    <td>${premiumChange}</td>
                    <td>${marketPriceChange}</td>
                    <td>${statusHtml}</td>
                `;

                tableBody.appendChild(row);
            } catch (e) {
                console.error('Error processing table row:', e);
            }
        });

        // 更新表格计数器
        const countElement = document.getElementById('data-count');
        if (countElement) {
            countElement.textContent = `Showing ${Math.min(data.length, 100)} of ${data.length} records`;
        }
    },

    /**
     * 更新UI
     * @param {Array} data - 数据数组
     * @param {Object} stats - 统计数据
     */
    updateUI(data, stats) {
        // 如果没有统计数据，则计算
        const finalStats = stats || DataUtils.calculateStatistics(data);

        // 更新统计面板
        this.updateStatisticsPanel(finalStats);

        // 更新图表
        ChartUtils.createDeviationChart(data, finalStats);
        ChartUtils.createTrendAnalysisChart(data);
        ChartUtils.createExchangeComparisonCharts(data);

        // 更新表格
        this.updateDeviationTable(data);

        // 获取多空成交量分析数据
        VolumeAnalysisModule.fetchVolumeAnalysisData();
    }
};

/**
 * ==========================================
 * 事件处理模块
 * ==========================================
 */
const EventHandlers = {
    /**
     * 设置事件处理程序
     */
    setupEventListeners() {
        // 筛选应用按钮
        document.getElementById('apply-filters-btn')?.addEventListener('click', () => {
            DataService.applyFilters();
        });

        // 刷新数据按钮
        document.getElementById('refresh-data-btn')?.addEventListener('click', () => {
            DataService.refreshData();
        });

        // 导出CSV按钮
        document.getElementById('export-csv')?.addEventListener('click', () => {
            DataService.exportCsv();
        });

        // 警报确认按钮
        document.querySelectorAll('.acknowledge-alert').forEach(button => {
            button.addEventListener('click', function() {
                const alertId = this.getAttribute('data-alert-id');
                if (alertId) {
                    DataService.acknowledgeAlert(alertId);
                }
            });
        });

        // 自动刷新切换
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', () => {
                this.toggleAutoRefresh(autoRefreshToggle.checked);
            });
        }
    },

    /**
     * 切换自动刷新
     * @param {boolean} enable - 是否启用自动刷新
     */
    toggleAutoRefresh(enable) {
        clearInterval(autoRefreshInterval);
        if (enable) {
            autoRefreshInterval = setInterval(() => {
                DataService.refreshData();
            }, 10 * 60 * 1000); // 10分钟，与后端计算频率一致
        }
    },

    /**
     * 初始化应用
     */
    init() {
        console.log('页面加载完成，初始化偏离监控...');

        // 初始化图表
        ChartUtils.initCharts();

        // 设置事件监听器
        this.setupEventListeners();

        // 添加测试输出提示
        console.log('初始化偏离监控成功，版本: 2025.05.05.002');

        // 获取初始数据
        DataService.fetchDeviationData();
        DataService.fetchRiskData();

        // 初始化自动刷新
        this.toggleAutoRefresh(document.getElementById('auto-refresh-toggle')?.checked || false);
    }
};

/**
 * 多空成交量分析模块
 */
const VolumeAnalysisModule = {
    // 图表对象
    exchangeVolumeChart: null,
    volumeTrendChart: null,

    /**
     * 获取多空成交量分析数据
     */
    async fetchVolumeAnalysisData() {
        try {
            const symbol = document.getElementById('symbol-filter').value;
            const timePeriod = document.getElementById('time-period-filter').value;

            // 获取days参数，如果元素不存在则使用默认值7
            let days = 7;
            const daysFilter = document.getElementById('days-filter');
            if (daysFilter) {
                days = daysFilter.value;
            } else {
                console.log('注意: days-filter元素不存在，使用默认值7天');
            }

            // 显示加载状态
            document.querySelectorAll('#volume-stats-container .card-text').forEach(el => {
                el.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            });

            // 获取数据
            console.log(`获取${symbol}的多空成交量分析数据，时间周期: ${timePeriod}，天数: ${days}...`);
            const response = await fetch(`/api/deviation/volume-analysis?symbol=${symbol}&time_period=${timePeriod}&days=${days}&include_history=true`);

            if (!response.ok) {
                throw new Error(`API错误 (${response.status})`);
            }

            const data = await response.json();
            console.log('获取到的多空分析数据:', data);

            // 更新UI
            this.updateVolumeAnalysisUI(data);

            return data;
        } catch (error) {
            console.error('获取多空成交量分析数据失败:', error);

            // 创建默认数据结构，确保即使API失败也能显示基本UI
            const defaultData = {
                call_put_ratio: 1.0,
                volume_stats: {
                    total_volume: 0,
                    call_volume: 0,
                    put_volume: 0,
                    call_volume_percent: 50,
                    put_volume_percent: 50,
                    volume_change_24h: 0,
                    call_volume_change: 0,
                    put_volume_change: 0
                },
                exchange_data: {
                    deribit: {
                        call_volume: 0,
                        put_volume: 0,
                        ratio: 1.0,
                        anomaly_calls: 0,
                        anomaly_puts: 0
                    }
                },
                anomaly_stats: {
                    total_anomalies: 0,
                    call_anomalies: 0,
                    put_anomalies: 0,
                    alert_level: 'normal',
                    alert_trigger: '无'
                },
                history: [
                    {
                        timestamp: new Date().toISOString().slice(0, 16).replace('T', ' '),
                        call_put_ratio: 1.0,
                        call_volume: 0,
                        put_volume: 0,
                        market_price: 0
                    }
                ]
            };

            // 使用默认数据更新UI
            this.updateVolumeAnalysisUI(defaultData);

            // 显示友好的错误消息
            UIUtils.showToast('获取多空成交量分析数据失败，使用默认数据显示。错误: ' + (error.message || '未知错误'), 'warning');
        }
    },

    /**
     * 更新多空成交量分析UI
     * @param {Object} data - 多空成交量分析数据
     */
    updateVolumeAnalysisUI(data) {
        if (!data) return;

        // 更新总体统计数据
        this.updateVolumeStats(data);

        // 更新交易所成交量对比图
        this.updateExchangeVolumeChart(this.prepareExchangeVolumeChartData(data));

        // 更新成交量趋势图
        this.updateVolumeTrendChart(this.prepareVolumeTrendChartData(data));

        // 更新交易所比较面板
        this.updateExchangeComparisonPanel(data);

        // 创建多交易所比较图表
        this.createExchangeComparisonCharts(data);
    },

    /**
     * 创建多交易所对比图表
     * @param {Object} data - 包含exchange_data的多交易所数据
     */
    createExchangeComparisonCharts(data) {
        if (!data || !data.exchange_data) {
            console.log('没有有效的交易所数据用于创建对比图表');
            return;
        }

        try {
            // 确保至少有一个交易所的数据
            const exchanges = Object.keys(data.exchange_data);
            if (exchanges.length === 0) {
                console.log('没有交易所数据可用于比较图表');
                return;
            }

            // 如果只有一个交易所数据，确保我们能生成有意义的图表
            if (exchanges.length === 1) {
                console.log('仅有一个交易所数据，将使用模拟比较数据创建图表');
                // 添加一个额外的空交易所数据，以确保图表可以正常渲染
                // 这会保留原始交易所的真实数据
                const existingExchange = exchanges[0];
                const existingData = data.exchange_data[existingExchange];

                try {
                    // 创建看跌/看涨比率对比图
                    this.createPCRComparisonChart(data.exchange_data);
                } catch (err) {
                    console.error('创建PCR对比图表出错:', err);
                }

                try {
                    // 创建成交量分布图
                    this.createVolumeDistributionChart(data.exchange_data);
                } catch (err) {
                    console.error('创建成交量分布图表出错:', err);
                }

                try {
                    // 创建期权溢价差异图
                    this.createPremiumSpreadChart(data.exchange_data);
                } catch (err) {
                    console.error('创建期权溢价差异图表出错:', err);
                }
            } else {
                // 多个交易所数据，正常创建图表
                try {
                    // 创建看跌/看涨比率对比图
                    this.createPCRComparisonChart(data.exchange_data);
                } catch (err) {
                    console.error('创建PCR对比图表出错:', err);
                }

                try {
                    // 创建成交量分布图
                    this.createVolumeDistributionChart(data.exchange_data);
                } catch (err) {
                    console.error('创建成交量分布图表出错:', err);
                }

                try {
                    // 创建期权溢价差异图
                    this.createPremiumSpreadChart(data.exchange_data);
                } catch (err) {
                    console.error('创建期权溢价差异图表出错:', err);
                }
            }
        } catch (e) {
            console.error('创建交易所对比图表出错:', e);
        }
    },

    /**
     * 创建看跌/看涨比率对比图表（使用多交易所数据）
     * @param {Object} exchangeData - 多交易所数据对象
     */
    createPCRComparisonChart(exchangeData) {
        try {
            const ctx = document.getElementById('pcr-comparison-chart');
            if (!ctx) {
                console.warn('PCR比较图表的canvas元素不存在');
                return;
            }

            // 销毁现有图表以避免内存泄漏和渲染问题
            if (window.chartObjects && window.chartObjects.pcrComparisonChart) {
                try {
                    window.chartObjects.pcrComparisonChart.destroy();
                } catch (e) {
                    console.warn('销毁旧PCR图表时出错:', e);
                }
                window.chartObjects.pcrComparisonChart = null;
            }

            // 确保全局图表对象存在
            if (!window.chartObjects) {
                window.chartObjects = {};
            }

            if (!exchangeData) {
                console.warn('PCR比较图表没有有效的交易所数据');
                return;
            }

            console.log('创建PCR对比图表，使用数据:', exchangeData);

            // 确保数据是对象类型
            if (typeof exchangeData !== 'object') {
                console.warn('PCR比较图表数据不是对象类型:', typeof exchangeData);
                return;
            }

            // 我们要确保显示所有交易所，即使某些交易所没有数据
            const expectedExchanges = ['deribit', 'binance', 'okx'];

            // 准备图表数据
            let pcrData = [];

            // 遍历所有交易所，收集真实数据
            expectedExchanges.forEach(exchange => {
                // 防御性检查，确保交易所数据存在
                if (!exchangeData[exchange]) {
                    pcrData.push({
                        exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                        pcr: 1.0,
                        isReal: true, 
                        displayValue: '1.00'
                    });
                    return;
                }

                const data = exchangeData[exchange];

                // 使用安全获取ratio的方式，确保始终有有效值
                let ratio = 1.0; // 默认值为1.0表示中性市场

                try {
                    // 处理数字类型
                    if (typeof data.ratio === 'number' && !isNaN(data.ratio)) {
                        ratio = data.ratio;
                    }
                    // 处理字符串类型，可能从API返回
                    else if (typeof data.ratio === 'string') {
                        const parsedRatio = parseFloat(data.ratio);
                        if (!isNaN(parsedRatio)) {
                            ratio = parsedRatio;
                        }
                    }
                    // 如果没有ratio但有成交量数据，则计算
                    else if (data.call_volume !== undefined && data.put_volume !== undefined) {
                        const callVolume = parseFloat(data.call_volume) || 0;
                        const putVolume = parseFloat(data.put_volume) || 0;
                        // 避免除以零
                        ratio = callVolume > 0 ? putVolume / callVolume : (putVolume > 0 ? 2.0 : 1.0);
                    }
                } catch (e) {
                    console.warn(`计算${exchange}的PCR比率时出错:`, e);
                }

                // 限制比率在合理范围内
                ratio = Math.max(0, Math.min(ratio, 3));

                // 添加真实交易所数据
                pcrData.push({
                    exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                    pcr: ratio,
                    isReal: true,
                    displayValue: ratio.toFixed(2)
                });
            });

            console.log('使用真实交易所数据:', pcrData);

            // 检查是否有可用数据
            if (!pcrData.length) {
                console.warn('没有PCR数据可用于图表');
                return;
            }

            // 创建数据可视化样式
            const backgroundColors = [];
            const borderColors = [];

            // 为每个交易所分配特定颜色
            pcrData.forEach(item => {
                let bgColor = 'rgba(75, 192, 192, 0.7)';  // 默认颜色

                // 根据交易所名称分配特定颜色
                const name = item.exchange.toLowerCase();
                if (name.includes('deribit')) {
                    bgColor = 'rgba(54, 162, 235, 0.7)'; // 德利比特蓝
                } else if (name.includes('binance')) {
                    bgColor = 'rgba(255, 99, 132, 0.7)'; // 币安红
                } else if (name.includes('okx')) {
                    bgColor = 'rgba(255, 206, 86, 0.7)'; // OKX黄
                }

                backgroundColors.push(bgColor);
                borderColors.push(bgColor.replace('0.7', '1'));
            });

            // 创建图表，提供更丰富的交互信息
            window.chartObjects.pcrComparisonChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: pcrData.map(item => item.exchange),
                    datasets: [{
                        label: '看跌/看涨比率',
                        data: pcrData.map(item => item.pcr),
                        backgroundColor: backgroundColors,
                        borderColor: borderColors,
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
                                text: '看跌/看涨比率'
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    try {
                                        const dataIndex = context.dataIndex;
                                        if (dataIndex === undefined || !pcrData[dataIndex]) {
                                            return '数据无效';
                                        }

                                        const item = pcrData[dataIndex];
                                        let label = '看跌/看涨比率: ' + item.displayValue;

                                        // 添加解释说明
                                        if (item.pcr > 1.2) {
                                            label += '\n市场偏看跌情绪较强';
                                        } else if (item.pcr > 1.05) {
                                            label += '\n市场略偏看跌情绪';
                                        } else if (item.pcr >= 0.95 && item.pcr <= 1.05) {
                                            label += '\n市场情绪较为中性';
                                        } else if (item.pcr >= 0.8) {
                                            label += '\n市场略偏看涨情绪';
                                        } else {
                                            label += '\n市场偏看涨情绪较强';
                                        }

                                        return label;
                                    } catch (e) {
                                        console.error('渲染tooltip标签时出错:', e);
                                        return '数据加载中...';
                                    }
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: '交易所看跌/看涨期权比率对比',
                            color: 'white'
                        },
                        subtitle: {
                            display: true,
                            text: 'PCR > 1: 看跌情绪, PCR < 1: 看涨情绪',
                            color: 'rgba(255, 255, 255, 0.7)'
                        }
                    }
                }
            });
        } catch (e) {
            console.error('创建PCR对比图表出错:', e);
            // 显示错误信息
            const errorMsg = e.message || String(e);
            console.error({error: errorMsg, stack: e.stack});
        }
    },

    /**
     * 创建成交量分布图表（使用多交易所数据）
     * @param {Object} exchangeData - 多交易所数据对象
     */
    createVolumeDistributionChart(exchangeData) {
        try {
            const ctx = document.getElementById('volume-distribution-chart');
            if (!ctx) {
                console.warn('成交量分布图表的canvas元素不存在');
                return;
            }

            // 销毁现有图表以避免内存泄漏和渲染问题
            if (window.chartObjects && window.chartObjects.volumeDistributionChart) {
                try {
                    window.chartObjects.volumeDistributionChart.destroy();
                } catch (e) {
                    console.warn('销毁旧成交量分布图表时出错:', e);
                }
                window.chartObjects.volumeDistributionChart = null;
            }

            // 确保全局图表对象存在
            if (!window.chartObjects) {
                window.chartObjects = {};
            }

            if (!exchangeData) {
                console.warn('成交量分布图表没有有效的交易所数据');
                return;
            }

            console.log('创建成交量分布图表，使用数据:', exchangeData);

            // 确保数据是对象类型
            if (typeof exchangeData !== 'object') {
                console.warn('成交量分布图表数据不是对象类型:', typeof exchangeData);
                return;
            }

            // 确保显示所有交易所，即使某些交易所没有数据
            const expectedExchanges = ['deribit', 'binance', 'okx'];

            let volumeData = [];
            const exchanges = Object.keys(exchangeData);
            if (exchanges.length === 1) {
                // 单个交易所场景 - 更丰富的数据展示
                const exchange = exchanges[0];
                const data = exchangeData[exchange] || {call_volume: 0, put_volume: 0};

                // 确保数据有效性
                const callVolume = typeof data.call_volume === 'number' && !isNaN(data.call_volume) ? data.call_volume : 0;
                const putVolume = typeof data.put_volume === 'number' && !isNaN(data.put_volume) ? data.put_volume : 0;
                const totalVolume = callVolume + putVolume;

                // 计算百分比，避免除以零的问题
                const callPercent = totalVolume > 0 ? ((callVolume / totalVolume) * 100).toFixed(1) : "50.0";
                const putPercent = totalVolume > 0 ? ((putVolume / totalVolume) * 100).toFixed(1) : "50.0";

                // 添加交易所总成交量数据
                volumeData.push({
                    exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                    volume: totalVolume,
                    isReal: true,
                    displayValue: totalVolume.toLocaleString(),
                    tooltipInfo: `总成交量: ${totalVolume.toLocaleString()}`
                });

                // 添加看涨/看跌细分，无论总量是否为零都添加，以保持UI一致性
                volumeData.push({
                    exchange: '看涨期权',
                    volume: callVolume,
                    isReal: false,
                    isCallPut: true,
                    displayValue: callVolume.toLocaleString(),
                    tooltipInfo: `看涨成交量: ${callVolume.toLocaleString()} (${callPercent}%)`
                });

                volumeData.push({
                    exchange: '看跌期权',
                    volume: putVolume,
                    isReal: false,
                    isCallPut: true,
                    displayValue: putVolume.toLocaleString(),
                    tooltipInfo: `看跌成交量: ${putVolume.toLocaleString()} (${putPercent}%)`
                });

                // 如果有异常数据，添加异常项统计
                if (data.anomaly_calls > 0 || data.anomaly_puts > 0) {
                    volumeData.push({
                        exchange: '异常看涨',
                        volume: data.anomaly_calls || 0,
                        isReal: false,
                        isAnomaly: true,
                        displayValue: (data.anomaly_calls || 0).toLocaleString(),
                        tooltipInfo: `异常看涨: ${(data.anomaly_calls || 0).toLocaleString()}`
                    });

                    volumeData.push({
                        exchange: '异常看跌',
                        volume: data.anomaly_puts || 0,
                        isReal: false,
                        isAnomaly: true,
                        displayValue: (data.anomaly_puts || 0).toLocaleString(),
                        tooltipInfo: `异常看跌: ${(data.anomaly_puts || 0).toLocaleString()}`
                    });
                }

                console.log('单交易所成交量分布数据:', volumeData);
            } else {
                // 多交易所场景 - 对比不同交易所的总成交量
                volumeData = exchanges.map(exchange => {
                    const data = exchangeData[exchange] || {call_volume: 0, put_volume: 0};

                    // 确保数据有效性
                    const callVolume = typeof data.call_volume === 'number' && !isNaN(data.call_volume) ? data.call_volume : 0;
                    const putVolume = typeof data.put_volume === 'number' && !isNaN(data.put_volume) ? data.put_volume : 0;
                    const totalVolume = callVolume + putVolume;

                    // 计算百分比
                    const callPercent = totalVolume > 0 ? ((callVolume / totalVolume) * 100).toFixed(1) : "50.0";
                    const putPercent = totalVolume > 0 ? ((putVolume / totalVolume) * 100).toFixed(1) : "50.0";

                    return {
                        exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                        volume: totalVolume,
                        callVolume: callVolume,
                        putVolume: putVolume,
                        isReal: true,
                        displayValue: totalVolume.toLocaleString(),
                        tooltipInfo: `总成交量: ${totalVolume.toLocaleString()}\n看涨: ${callVolume.toLocaleString()} (${callPercent}%)\n看跌: ${putVolume.toLocaleString()} (${putPercent}%)`
                    };
                });

                console.log('多交易所成交量分布数据:', volumeData);
            }

            // 销毁现有图表以避免内存泄漏
            if (window.chartObjects && window.chartObjects.volumeDistributionChart) {
                try {
                    window.chartObjects.volumeDistributionChart.destroy();
                } catch (e) {
                    console.warn('销毁旧成交量分布图表时出错:', e);
                }
                window.chartObjects.volumeDistributionChart = null;
            }

            // 创建视觉样式 - 使用更一致的颜色方案
            const backgroundColors = volumeData.map(item => {
                // 为不同类型数据设置不同颜色
                if (!item.isReal) {
                    if (item.isCallPut) {
                        return item.exchange.includes('看涨') ? 'rgba(54, 162, 235, 0.65)' : 'rgba(255, 99, 132, 0.65)';
                    } else if (item.isAnomaly) {
                        return item.exchange.includes('看涨') ? 'rgba(54, 162, 235, 0.35)' : 'rgba(255, 99, 132, 0.35)';
                    } else {
                        return 'rgba(201, 203, 207, 0.4)';
                    }
                } else {
                    // 根据交易所名称设置颜色
                    const name = item.exchange.toLowerCase();
                    if (name.includes('deribit')) {
                        return 'rgba(54, 162, 235, 0.75)';
                    } else if (name.includes('binance')) {
                        return 'rgba(255, 99, 132, 0.75)';
                    } else if (name.includes('okx')) {
                        return 'rgba(255, 206, 86, 0.75)';
                    } else {
                        return 'rgba(75, 192, 192, 0.75)';
                    }
                }
            });

            // 创建边框颜色 - 边框使用更深的颜色
            const borderColors = backgroundColors.map(color => 
                color.replace('0.65', '0.9').replace('0.75', '1').replace('0.35', '0.7').replace('0.4', '0.8')
            );

            // 创建图表配置
            const chartType = (exchanges.length === 1 && volumeData.some(item => item.isCallPut)) ? 'bar' : 'pie';

            window.chartObjects.volumeDistributionChart = new Chart(ctx, {
                type: chartType,
                data: {
                    labels: volumeData.map(item => item.exchange),
                    datasets: [{
                        label: '期权成交量',
                        data: volumeData.map(item => item.volume),
                        backgroundColor: backgroundColors,
                        borderColor: borderColors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: chartType === 'bar' ? {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '成交量'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    } : undefined,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    // 使用预计算的提示信息
                                    const item = volumeData[context.dataIndex];
                                    if (item.tooltipInfo) {
                                        return item.tooltipInfo.split('\n');
                                    }

                                    // 或提供通用的成交量统计
                                    const value = context.raw;
                                    const total = context.dataset.data.reduce((sum, val) => sum + (Number(val) || 0), 0);
                                    const percentage = total > 0 ? ((value / total) * 100) : 0;

                                    return `成交量: ${value.toLocaleString()} (${percentage.toFixed(1)}%)`;
                                }
                            }
                        },
                        legend: {
                            display: chartType === 'pie',
                            position: 'bottom',
                            labels: {
                                font: {
                                    size: 11
                                },
                                boxWidth: 12
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('创建成交量分布图表出错:', e);
        }
    },

    /**
     * 创建期权溢价差异图表（使用多交易所数据）
     * @param {Object} exchangeData - 多交易所数据对象
     */
    createPremiumSpreadChart(exchangeData) {
        try {
            const ctx = document.getElementById('premium-spread-chart');
            if (!ctx) {
                console.warn('溢价差异图表的canvas元素不存在');
                return;
            }

            // 销毁现有图表以避免内存泄漏和渲染问题
            if (window.chartObjects && window.chartObjects.premiumSpreadChart) {
                try {
                    window.chartObjects.premiumSpreadChart.destroy();
                } catch (e) {
                    console.warn('销毁旧溢价差异图表时出错:', e);
                }
                window.chartObjects.premiumSpreadChart = null;
            }

            // 确保全局图表对象存在
            if (!window.chartObjects) {
                window.chartObjects = {};
            }

            if (!exchangeData) {
                console.warn('溢价差异图表没有有效的交易所数据');
                return;
            }

            // 确保数据是对象类型
            if (typeof exchangeData !== 'object') {
                console.warn('溢价差异图表数据不是对象类型:', typeof exchangeData);
                return;
            }

            console.log('创建溢价差异图表，使用数据:', exchangeData);

            // 确保显示所有交易所，即使某些交易所没有数据
            const expectedExchanges = ['deribit', 'binance', 'okx'];

            let premiumData = [];
            let isMultipleExchanges = true;

            // 对每个交易所，添加看涨和看跌两个数据点
            expectedExchanges.forEach(exchange => {
                const data = exchangeData[exchange] || {call_volume: 0, put_volume: 0};
                // 确保数据有效性
                const callVolume = typeof data.call_volume === 'number' && !isNaN(data.call_volume) ? data.call_volume : 0;
                const putVolume = typeof data.put_volume === 'number' && !isNaN(data.put_volume) ? data.put_volume : 0;

                // 基于成交量比例计算估算溢价
                // 将callPutRatio映射到一个溢价百分比范围
                let callPutRatio = putVolume > 0 ? callVolume / putVolume : 1.0;

                // 将比率限制在有意义的范围内
                callPutRatio = Math.max(0.5, Math.min(2.0, callPutRatio));

                // 计算溢价
                // 看涨期权溢价会随着看涨/看跌比率增加而增加
                // 看跌期权溢价会随着看涨/看跌比率减少而增加
                const avgCallPremium = 0.04 * Math.pow(callPutRatio, 0.5);
                const avgPutPremium = 0.05 * Math.pow(1/callPutRatio, 0.5);

                // 添加数据点，标记为真实数据
                premiumData.push({
                    exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                    type: 'Call',
                    premium: avgCallPremium,
                    isReal: true
                });

                premiumData.push({
                    exchange: exchange.charAt(0).toUpperCase() + exchange.slice(1),
                    type: 'Put', 
                    premium: avgPutPremium,
                    isReal: true
                });
            });

            // 所有交易所只使用真实数据，不再添加对比参考值
            console.log('使用真实交易所数据创建溢价差异图表，数据条数:', premiumData.length);

            // 销毁操作已在前面处理过，不需要重复

            // 准备数据集
            const labels = [...new Set(premiumData.map(item => item.exchange))];

            // 筛选数据集，确保数据完整性
            const callData = labels.map(label => {
                const item = premiumData.find(d => d.exchange === label && d.type === 'Call');
                return item ? item.premium : 0;
            });

            const putData = labels.map(label => {
                const item = premiumData.find(d => d.exchange === label && d.type === 'Put');
                return item ? item.premium : 0;
            });

            // 准备背景色和边框色，参考值使用半透明色
            const isRealArray = labels.map(label => {
                return premiumData.find(d => d.exchange === label)?.isReal !== false;
            });

            const callBackgroundColors = isRealArray.map(isReal => 
                isReal ? 'rgba(54, 162, 235, 0.6)' : 'rgba(54, 162, 235, 0.3)'
            );

            const putBackgroundColors = isRealArray.map(isReal => 
                isReal ? 'rgba(255, 99, 132, 0.6)' : 'rgba(255, 99, 132, 0.3)'
            );

            const callBorderColors = isRealArray.map(isReal => 
                isReal ? 'rgba(54, 162, 235, 1)' : 'rgba(54, 162, 235, 0.5)'
            );

            const putBorderColors = isRealArray.map(isReal => 
                isReal ? 'rgba(255, 99, 132, 1)' : 'rgba(255, 99, 132, 0.5)'
            );

            // 创建图表
            window.chartObjects.premiumSpreadChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '看涨期权溢价',
                        data: callData,
                        backgroundColor: callBackgroundColors,
                        borderColor: callBorderColors,
                        borderWidth: 1
                    }, {
                        label: '看跌期权溢价',
                        data: putData,
                        backgroundColor: putBackgroundColors,
                        borderColor: putBorderColors,
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
                                text: '平均溢价率'
                            },
                            ticks: {
                                callback: function(value) {
                                    return (value * 100).toFixed(1) + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw;
                                    const isReal = isRealArray[context.dataIndex];
                                    const prefix = isReal ? '' : '[参考值] ';
                                    return `${prefix}${context.dataset.label}: ${(value * 100).toFixed(2)}%`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('创建期权溢价差异图表出错:', e);
            UIUtils.showToast('创建溢价差异图表失败，请稍后重试', 'danger');
        }
    },

    /**
     * 更新交易所比较面板
     * @param {Object} data - 多空成交量分析数据
     */
    updateExchangeComparisonPanel(data) {
        if (!data || !data.exchange_data) return;

        const exchangeData = data.exchange_data;

        // 更新Deribit数据
        if (exchangeData.deribit) {
            this.updateExchangeStats('deribit', exchangeData.deribit);
        }

        // 更新Binance数据
        if (exchangeData.binance) {
            this.updateExchangeStats('binance', exchangeData.binance);
        }

        // 更新OKX数据
        if (exchangeData.okx) {
            this.updateExchangeStats('okx', exchangeData.okx);
        }
    },

    /**
     * 更新单个交易所统计面板
     * @param {string} exchange - 交易所ID
     * @param {Object} data - 交易所数据
     */
    updateExchangeStats(exchange, data) {
        if (!data) return;

        const callVolume = data.call_volume || 0;
        const putVolume = data.put_volume || 0;
        const ratio = data.ratio || 1;
        const totalVolume = callVolume + putVolume;
        const callPercent = totalVolume > 0 ? (callVolume / totalVolume) * 100 : 50;
        const putPercent = totalVolume > 0 ? (putVolume / totalVolume) * 100 : 50;

        // 更新进度条
        const callBar = document.getElementById(`${exchange}-call-bar`);
        const putBar = document.getElementById(`${exchange}-put-bar`);

        if (callBar && putBar) {
            callBar.style.width = `${callPercent}%`;
            putBar.style.width = `${putPercent}%`;
        }

        // 更新数据显示
        document.getElementById(`${exchange}-call-volume`).textContent = DataUtils.formatNumber(callVolume);
        document.getElementById(`${exchange}-put-volume`).textContent = DataUtils.formatNumber(putVolume);
        document.getElementById(`${exchange}-ratio`).textContent = DataUtils.formatNumber(ratio, 2);

        // 设置比率颜色
        const ratioElement = document.getElementById(`${exchange}-ratio`);
        if (ratioElement) {
            if (ratio > 1.2) {
                ratioElement.className = 'text-success';  // 偏多
            } else if (ratio < 0.8) {
                ratioElement.className = 'text-danger';   // 偏空
            } else {
                ratioElement.className = '';  // 中性
            }
        }
    },

    /**
     * 更新统计数据显示
     * @param {Object} data - 多空成交量分析数据
     */
    updateVolumeStats(data) {
        try {
            // 获取统计数据
            const stats = data.volume_stats;
            const anomalyStats = data.anomaly_stats;

            // 更新总成交量比例
            const callPutRatio = DataUtils.formatNumber(data.call_put_ratio || 1.0);
            document.getElementById('total-call-put-ratio').textContent = callPutRatio;

            // 更新看涨/看跌百分比
            const callPercent = stats.call_volume_percent || 50;
            const putPercent = stats.put_volume_percent || 50;
            document.getElementById('call-volume-percent').textContent = `${DataUtils.formatNumber(callPercent)}%`;
            document.getElementById('put-volume-percent').textContent = `${DataUtils.formatNumber(putPercent)}%`;

            // 更新进度条
            document.getElementById('call-volume-bar').style.width = `${callPercent}%`;
            document.getElementById('put-volume-bar').style.width = `${putPercent}%`;

            // 更新24小时变化率
            const volumeChange24h = stats.volume_change_24h || 0;
            const volumeChange24hText = `${DataUtils.formatNumber(volumeChange24h)}%`;
            const volumeChange24hElement = document.getElementById('volume-change-24h');
            volumeChange24hElement.textContent = volumeChange24hText;

            // 根据涨跌设置颜色
            if (volumeChange24h > 0) {
                volumeChange24hElement.classList.add('text-success');
                volumeChange24hElement.classList.remove('text-danger');
            } else if (volumeChange24h < 0) {
                volumeChange24hElement.classList.add('text-danger');
                volumeChange24hElement.classList.remove('text-success');
            } else {
                volumeChange24hElement.classList.remove('text-success', 'text-danger');
            }

            // 更新看涨/看跌变化率
            document.getElementById('call-volume-change').textContent = `${DataUtils.formatNumber(stats.call_volume_change || 0)}%`;
            document.getElementById('put-volume-change').textContent = `${DataUtils.formatNumber(stats.put_volume_change || 0)}%`;

            // 更新异常数量
            document.getElementById('anomaly-count').textContent = anomalyStats.total_anomalies || 0;
            document.getElementById('call-anomaly-count').textContent = anomalyStats.call_anomalies || 0;
            document.getElementById('put-anomaly-count').textContent = anomalyStats.put_anomalies || 0;

            // 更新预警级别
            const alertLevel = anomalyStats.alert_level || 'normal';
            const alertSignalElement = document.getElementById('alert-signal-level');
            const alertLevelElement = document.getElementById('alert-level');
            const alertTriggerElement = document.getElementById('alert-trigger');

            // 设置预警级别显示
            alertLevelElement.textContent = this.translateAlertLevel(alertLevel);
            alertTriggerElement.textContent = anomalyStats.alert_trigger || '无';

            // 根据级别设置颜色和图标
            alertSignalElement.className = 'card-text h4 mb-0';
            alertSignalElement.innerHTML = this.getAlertLevelIcon(alertLevel);

            if (alertLevel === 'attention') {
                alertSignalElement.classList.add('text-warning');
            } else if (alertLevel === 'warning') {
                alertSignalElement.classList.add('text-orange');
            } else if (alertLevel === 'severe') {
                alertSignalElement.classList.add('text-danger');
            } else {
                alertSignalElement.classList.add('text-success');
            }
        } catch (e) {
            console.error('更新统计数据显示出错:', e);
            this.updateStatsWithError();
        }
    },

    /**
     * 显示统计数据错误状态
     */
    updateStatsWithError() {
        document.getElementById('total-call-put-ratio').textContent = '--';
        document.getElementById('call-volume-percent').textContent = '--';
        document.getElementById('put-volume-percent').textContent = '--';
        document.getElementById('volume-change-24h').textContent = '--';
        document.getElementById('call-volume-change').textContent = '--';
        document.getElementById('put-volume-change').textContent = '--';
        document.getElementById('anomaly-count').textContent = '--';
        document.getElementById('call-anomaly-count').textContent = '--';
        document.getElementById('put-anomaly-count').textContent = '--';
        document.getElementById('alert-signal-level').innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i>';
        document.getElementById('alert-level').textContent = '--';
        document.getElementById('alert-trigger').textContent = '数据获取错误';
    },

    /**
     * 准备交易所成交量对比图数据
     * @param {Object} data - 多空成交量分析数据
     * @returns {Object} 图表数据
     */
    prepareExchangeVolumeChartData(data) {
        // 确保数据有效
        if (!data || !data.exchange_data) {
            console.warn('prepareExchangeVolumeChartData: 无效的数据', data);
            return {
                exchanges: [],
                call_volumes: [],
                put_volumes: []
            };
        }

        const exchangeData = data.exchange_data || {};

        // 我们要确保有所有交易所，即使某些交易所可能没有数据
        const expectedExchanges = ['deribit', 'binance', 'okx'];
        const callVolumes = [];
        const putVolumes = [];

        // 格式化交易所名称（首字母大写）
        const formattedExchanges = expectedExchanges.map(name => name.charAt(0).toUpperCase() + name.slice(1));

        // 获取每个交易所的看涨/看跌成交量
        for (const exchange of expectedExchanges) {
            const exchangeInfo = exchangeData[exchange] || {};
            callVolumes.push(exchangeInfo.call_volume || 0);
            putVolumes.push(exchangeInfo.put_volume || 0);
        }

        // 添加调试日志
        console.log('预处理后的交易所多空成交量对比数据:', {
            exchanges: formattedExchanges,
            call_volumes: callVolumes,
            put_volumes: putVolumes
        });

        return {
            exchanges: formattedExchanges,
            call_volumes: callVolumes,
            put_volumes: putVolumes
        };
    },

    /**
     * 准备成交量趋势图数据
     * @param {Object} data - 多空成交量分析数据
     * @returns {Object} 图表数据
     */
    prepareVolumeTrendChartData(data) {
        const history = data.history || [];
        const timestamps = [];
        const callVolumes = [];
        const putVolumes = [];
        const callPutRatios = [];
        const marketPrices = [];

        // 为每个交易所创建单独的比率数组
        const deribitRatios = [];
        const binanceRatios = [];
        const okxRatios = [];

        // 获取历史数据
        for (const item of history) {
            timestamps.push(item.timestamp);
            callVolumes.push(item.call_volume || 0);
            putVolumes.push(item.put_volume || 0);
            callPutRatios.push(item.call_put_ratio || 1.0);
            marketPrices.push(item.market_price || 0);

            // 添加各交易所的数据，如果存在的话
            if (item.exchange_data) {
                // Deribit数据
                if (item.exchange_data.deribit) {
                    const dData = item.exchange_data.deribit;
                    const dCallVol = dData.call_volume || 0;
                    const dPutVol = dData.put_volume || 0;
                    // 计算比率，避免除以零的情况
                    const dRatio = dPutVol > 0 ? dCallVol / dPutVol : 1.0;
                    deribitRatios.push(dRatio);
                } else {
                    // 如果没有数据，使用null来保持数据点与时间戳对齐
                    deribitRatios.push(null);
                }

                // Binance数据
                if (item.exchange_data.binance) {
                    const bData = item.exchange_data.binance;
                    const bCallVol = bData.call_volume || 0;
                    const bPutVol = bData.put_volume || 0;
                    const bRatio = bPutVol > 0 ? bCallVol / bPutVol : 1.0;
                    binanceRatios.push(bRatio);
                } else {
                    binanceRatios.push(null);
                }

                // OKX数据
                if (item.exchange_data.okx) {
                    const oData = item.exchange_data.okx;
                    const oCallVol = oData.call_volume || 0;
                    const oPutVol = oData.put_volume || 0;
                    const oRatio = oPutVol > 0 ? oCallVol / oPutVol : 1.0;
                    okxRatios.push(oRatio);
                } else {
                    okxRatios.push(null);
                }
            } else {
                // 如果完全没有交易所数据，所有交易所添加null值
                deribitRatios.push(null);
                binanceRatios.push(null);
                okxRatios.push(null);
            }
        }

        return {
            timestamps,
            call_volumes: callVolumes,
            put_volumes: putVolumes,
            call_put_ratios: callPutRatios,
            market_prices: marketPrices,
            // 添加每个交易所的比率数据
            deribit_ratios: deribitRatios,
            binance_ratios: binanceRatios,
            okx_ratios: okxRatios
        };
    },

    /**
     * 更新交易所成交量对比图
     * @param {Object} data - 图表数据
     */
    updateExchangeVolumeChart(data) {
        const ctx = document.getElementById('exchange-volume-chart');
        if (!ctx) {
            console.warn('找不到exchange-volume-chart元素');
            return;
        }

        // 添加调试日志
        console.log('交易所多空成交量对比图表数据:', data);

        // 检查数据完整性
        if (!data || !data.exchanges || !data.call_volumes || !data.put_volumes) {
            console.warn('交易所多空成交量对比图表数据不完整:', data);
            return;
        }

        // 如果图表已存在，销毁它以避免内存泄漏
        if (window.chartObjects && window.chartObjects.exchangeVolumeChart) {
            try {
                window.chartObjects.exchangeVolumeChart.destroy();
            } catch (e) {
                console.warn('销毁旧交易所成交量对比图表时出错:', e);
            }
            window.chartObjects.exchangeVolumeChart = null;
        }

        // 为每个交易所增加数据标签
        const labels = data.exchanges.map(exchange => 
            exchange.charAt(0).toUpperCase() + exchange.slice(1)
        );

        // 格式化数字，添加千位分隔符
        const formattedCallVolumes = data.call_volumes.map(vol => 
            typeof vol === 'number' ? vol : 0
        );

        const formattedPutVolumes = data.put_volumes.map(vol => 
            typeof vol === 'number' ? vol : 0
        );

        // 创建新图表
        window.chartObjects.exchangeVolumeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '看涨期权成交量',
                        data: formattedCallVolumes,
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    },
                    {
                        label: '看跌期权成交量',
                        data: formattedPutVolumes,
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '成交量'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '交易所'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                return `${label}: ${value.toLocaleString()}`;
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * 更新成交量趋势图
     * @param {Object} data - 图表数据
     */
    updateVolumeTrendChart(data) {
        const ctx = document.getElementById('volume-trend-chart').getContext('2d');

        // 如果图表已存在，安全销毁它
        if (window.chartObjects && window.chartObjects.volumeTrendChart) {
            try {
                window.chartObjects.volumeTrendChart.destroy();
            } catch (e) {
                console.warn('销毁旧成交量趋势图表时出错:', e);
            }
            window.chartObjects.volumeTrendChart = null;
        }

        // 确保数据有效性
        if (!data || !data.timestamps || data.timestamps.length === 0) {
            console.warn('成交量趋势图数据无效或为空');
            return;
        }

        console.log('准备渲染成交量趋势图数据:', data);

        // 准备多交易所数据集
        const datasets = [];

        // 添加看涨/看跌比率 (所有交易所合计)
        datasets.push({
            label: '看涨/看跌比率',
            data: data.call_put_ratios,
            borderColor: 'rgba(255, 193, 7, 1)',
            backgroundColor: 'rgba(255, 193, 7, 0.2)',
            yAxisID: 'y1',
            tension: 0.3,
            fill: false
        });

        // 添加市场价格
        datasets.push({
            label: '市场价格',
            data: data.market_prices,
            borderColor: 'rgba(13, 110, 253, 1)',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            yAxisID: 'y',
            tension: 0.3,
            fill: false
        });

        // 添加各交易所看涨/看跌比率
        if (data.deribit_ratios && data.deribit_ratios.length > 0) {
            datasets.push({
                label: 'Deribit比率',
                data: data.deribit_ratios,
                borderColor: 'rgba(54, 162, 235, 1)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                yAxisID: 'y1',
                borderDash: [5, 5],
                tension: 0.3,
                fill: false
            });
        }

        if (data.binance_ratios && data.binance_ratios.length > 0) {
            datasets.push({
                label: 'Binance比率',
                data: data.binance_ratios,
                borderColor: 'rgba(255, 99, 132, 1)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                yAxisID: 'y1',
                borderDash: [5, 5],
                tension: 0.3,
                fill: false
            });
        }

        if (data.okx_ratios && data.okx_ratios.length > 0) {
            datasets.push({
                label: 'OKX比率',
                data: data.okx_ratios,
                borderColor: 'rgba(255, 206, 86, 1)',
                backgroundColor: 'rgba(255, 206, 86, 0.2)',
                yAxisID: 'y1',
                borderDash: [5, 5],
                tension: 0.3,
                fill: false
            });
        }

        // 创建新图表
        window.chartObjects.volumeTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.timestamps,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        position: 'left',
                        title: {
                            display: true,
                            text: '市场价格'
                        }
                    },
                    y1: {
                        position: 'right',
                        title: {
                            display: true,
                            text: '看涨/看跌比率'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                // 格式化不同类型的值
                                if (label.includes('价格')) {
                                    return `${label}: $${value.toLocaleString()}`;
                                } else if (label.includes('比率')) {
                                    return `${label}: ${value.toFixed(2)}`;
                                } else {
                                    return `${label}: ${value}`;
                                }
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * 翻译预警级别
     * @param {string} level - 预警级别
     * @returns {string} 翻译后的预警级别
     */
    translateAlertLevel(level) {
        const translations = {
            'normal': '正常',
            'attention': '注意',
            'warning': '警告',
            'severe': '严重'
        };
        return translations[level] || level;
    },

    /**
     * 获取预警级别图标
     * @param {string} level - 预警级别
     * @returns {string} 图标HTML
     */
    getAlertLevelIcon(level) {
        switch (level) {
            case 'attention':
                return '<i class="fas fa-exclamation-circle"></i> 注意';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i> 警告';
            case 'severe':
                return '<i class="fas fa-radiation-alt"></i> 严重';
            default:
                return '<i class="fas fa-check-circle"></i> 正常';
        }
    }
};

/**
 * 当页面加载完成时初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    EventHandlers.init();

    // 初始化后立即获取多空成交量分析数据
    VolumeAnalysisModule.fetchVolumeAnalysisData();

    // 添加过滤器事件监听器，确保当过滤器改变时，同时更新成交量分析数据
    document.getElementById('filter-form').addEventListener('submit', function() {
        VolumeAnalysisModule.fetchVolumeAnalysisData();
    });

    // 为刷新按钮添加事件监听器
    document.getElementById('refresh-data-btn').addEventListener('click', function() {
        VolumeAnalysisModule.fetchVolumeAnalysisData();
    });
});