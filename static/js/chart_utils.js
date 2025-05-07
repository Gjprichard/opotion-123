
/**
 * 图表工具模块
 * 提供创建和管理图表的通用函数
 */
const ChartUtils = {
    /**
     * 初始化图表
     */
    initCharts() {
        // 确保全局图表对象存在
        if (!window.chartObjects) {
            window.chartObjects = {};
        }
    },

    /**
     * 销毁所有图表
     */
    destroyAllCharts() {
        if (!window.chartObjects) {
            window.chartObjects = {};
            return;
        }

        // 安全地销毁所有图表
        Object.keys(window.chartObjects).forEach(chartKey => {
            if (window.chartObjects[chartKey]) {
                try {
                    window.chartObjects[chartKey].destroy();
                } catch (e) {
                    console.warn(`销毁图表出错: ${chartKey}`, e);
                }
                window.chartObjects[chartKey] = null;
            }
        });
    },
    
    /**
     * 销毁特定图表
     * @param {string} chartKey - 图表键名
     */
    destroyChart(chartKey) {
        if (window.chartObjects && window.chartObjects[chartKey]) {
            try {
                window.chartObjects[chartKey].destroy();
            } catch (e) {
                console.warn(`销毁图表出错: ${chartKey}`, e);
            }
            window.chartObjects[chartKey] = null;
        }
    },
    
    /**
     * 创建或更新散点图
     * @param {string} canvasId - Canvas元素ID
     * @param {Array} datasets - 图表数据集
     * @param {Object} options - 图表配置选项
     * @param {string} chartKey - 存储在chartObjects中的键名
     */
    createOrUpdateBubbleChart(canvasId, datasets, options, chartKey) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) {
            console.warn(`Canvas元素未找到: ${canvasId}`);
            return null;
        }
        
        // 如果图表已存在则销毁
        this.destroyChart(chartKey);
        
        // 创建新图表
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const dataPoint = context.raw;
                            return [
                                `${dataPoint.optionTypeDisplay || '期权'} ${dataPoint.strike_price || ''}`,
                                `偏离率: ${dataPoint.deviation_percent?.toFixed(2)}%`,
                                `成交量变化: ${dataPoint.volume_change_percent?.toFixed(2)}%`,
                                `权利金: ${dataPoint.premium?.toFixed(4)}`
                            ];
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '偏离率 (%)'
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '成交量变化 (%)'
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.2)'
                    }
                }
            }
        };
        
        // 合并选项
        const mergedOptions = {...defaultOptions, ...options};
        
        // 创建图表
        window.chartObjects[chartKey] = new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: datasets
            },
            options: mergedOptions
        });
        
        return window.chartObjects[chartKey];
    },
    
    /**
     * 创建或更新折线图
     * @param {string} canvasId - Canvas元素ID
     * @param {Object} chartData - 图表数据
     * @param {Object} options - 图表配置选项
     * @param {string} chartKey - 存储在chartObjects中的键名
     */
    createOrUpdateLineChart(canvasId, chartData, options, chartKey) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) {
            console.warn(`Canvas元素未找到: ${canvasId}`);
            return null;
        }
        
        // 如果图表已存在则销毁
        this.destroyChart(chartKey);
        
        // 默认选项
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        };
        
        // 合并选项
        const mergedOptions = {...defaultOptions, ...options};
        
        // 创建图表
        window.chartObjects[chartKey] = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: mergedOptions
        });
        
        return window.chartObjects[chartKey];
    },
    
    /**
     * 计算趋势线
     * @param {Array} points - 数据点数组，每个点应包含x和y属性
     * @returns {Array} 趋势线点数组
     */
    calculateTrendLine(points) {
        if (!points || points.length < 2) return [];
        
        try {
            // 只使用有效数据点
            const validPoints = points.filter(p => 
                p.x !== undefined && p.y !== undefined && 
                !isNaN(p.x) && !isNaN(p.y)
            );
            
            if (validPoints.length < 2) return [];
            
            // 计算均值
            let sumX = 0, sumY = 0;
            for (const point of validPoints) {
                sumX += point.x;
                sumY += point.y;
            }
            const meanX = sumX / validPoints.length;
            const meanY = sumY / validPoints.length;
            
            // 计算斜率和截距
            let numerator = 0, denominator = 0;
            for (const point of validPoints) {
                numerator += (point.x - meanX) * (point.y - meanY);
                denominator += Math.pow(point.x - meanX, 2);
            }
            
            // 避免除以零
            if (Math.abs(denominator) < 0.0001) return [];
            
            const slope = numerator / denominator;
            const intercept = meanY - slope * meanX;
            
            // 获取x的最小值和最大值来确定趋势线的起点和终点
            const minX = Math.min(...validPoints.map(p => p.x));
            const maxX = Math.max(...validPoints.map(p => p.x));
            
            // 创建趋势线数据点
            return [
                { x: minX, y: slope * minX + intercept },
                { x: maxX, y: slope * maxX + intercept }
            ];
        } catch (e) {
            console.error('计算趋势线错误:', e);
            return [];
        }
    }
};

// 导出模块
window.ChartUtils = ChartUtils;
