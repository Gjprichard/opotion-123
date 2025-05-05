"""
Translation dictionary for supporting multiple languages
"""

translations = {
    # Common UI elements
    'dashboard': {
        'en': 'Dashboard',
        'zh': '仪表盘'
    },
    'alerts': {
        'en': 'Alerts',
        'zh': '预警'
    },
    'historical': {
        'en': 'Historical Data',
        'zh': '历史数据'
    },
    'scenario': {
        'en': 'Scenario Analysis',
        'zh': '情景分析'
    },
    'settings': {
        'en': 'Settings',
        'zh': '设置'
    },
    'language': {
        'en': 'Language',
        'zh': '语言'
    },
    'time_period': {
        'en': 'Time Period',
        'zh': '时间周期'
    },
    'symbol': {
        'en': 'Symbol',
        'zh': '交易对'
    },
    
    # Risk indicators
    'volaxivity': {
        'en': 'Volaxivity',
        'zh': '波动性指数'
    },
    'volatility_skew': {
        'en': 'Volatility Skew',
        'zh': '波动率偏斜'
    },
    'put_call_ratio': {
        'en': 'Put/Call Ratio',
        'zh': '看跌/看涨比率'
    },
    'reflexivity_indicator': {
        'en': 'Reflexivity',
        'zh': '反身性指标'
    },
    'market_sentiment': {
        'en': 'Market Sentiment',
        'zh': '市场情绪'
    },
    'funding_rate': {
        'en': 'Funding Rate',
        'zh': '资金费率'
    },
    'liquidation_risk': {
        'en': 'Liquidation Risk',
        'zh': '清算风险'
    },
    
    # Market states
    'risk-on': {
        'en': 'Risk-On',
        'zh': '风险偏好'
    },
    'risk-off': {
        'en': 'Risk-Off',
        'zh': '风险规避'
    },
    
    # Alert levels
    'attention': {
        'en': 'Attention',
        'zh': '注意'
    },
    'warning': {
        'en': 'Warning',
        'zh': '警告'
    },
    'severe': {
        'en': 'Severe',
        'zh': '严重'
    },
    
    # Crypto-specific
    'btc': {
        'en': 'Bitcoin',
        'zh': '比特币'
    },
    'eth': {
        'en': 'Ethereum',
        'zh': '以太坊'
    },
    
    # Button actions
    'refresh': {
        'en': 'Refresh',
        'zh': '刷新'
    },
    'save': {
        'en': 'Save',
        'zh': '保存'
    },
    'delete': {
        'en': 'Delete',
        'zh': '删除'
    },
    'run': {
        'en': 'Run',
        'zh': '运行'
    },
    'acknowledge': {
        'en': 'Acknowledge',
        'zh': '确认'
    },
    
    # Option types
    'call': {
        'en': 'Call',
        'zh': '看涨期权'
    },
    'put': {
        'en': 'Put',
        'zh': '看跌期权'
    },
    
    # Greeks
    'delta': {
        'en': 'Delta',
        'zh': 'Delta值'
    },
    'gamma': {
        'en': 'Gamma',
        'zh': 'Gamma值'
    },
    'theta': {
        'en': 'Theta',
        'zh': 'Theta值'
    },
    'vega': {
        'en': 'Vega',
        'zh': 'Vega值'
    },
    
    # Scenario analysis
    'price_change': {
        'en': 'Price Change (%)',
        'zh': '价格变化 (%)'
    },
    'volatility_change': {
        'en': 'Volatility Change (%)',
        'zh': '波动率变化 (%)'
    },
    'time_horizon': {
        'en': 'Time Horizon (Days)',
        'zh': '时间范围 (天)'
    },
    'estimated_pnl': {
        'en': 'Estimated P&L',
        'zh': '预计盈亏'
    },
    
    # Strike Deviation Monitor
    'strike_deviation': {
        'en': 'Strike Deviation',
        'zh': '执行价偏离'
    },
    'option_deviation_monitor': {
        'en': 'Option Strike Price Deviation Monitor',
        'zh': '期权执行价偏离监控'
    },
    'monitor_options_with_strike_prices_deviating': {
        'en': 'Monitor options with strike prices deviating',
        'zh': '监控执行价偏离市场价'
    },
    'from_market_price': {
        'en': 'from market price',
        'zh': '的期权合约'
    },
    'filters': {
        'en': 'Filters',
        'zh': '筛选条件'
    },
    'days': {
        'en': 'Days',
        'zh': '天数'
    },
    'day': {
        'en': 'Day',
        'zh': '天'
    },
    'days': {
        'en': 'Days',
        'zh': '天'
    },
    'show_anomalies_only': {
        'en': 'Show anomalies only',
        'zh': '仅显示异常'
    },
    'apply_filters': {
        'en': 'Apply Filters',
        'zh': '应用筛选'
    },
    'active_deviation_alerts': {
        'en': 'Active Deviation Alerts',
        'zh': '活跃偏离警报'
    },
    'no_active_deviation_alerts': {
        'en': 'No active deviation alerts',
        'zh': '无活跃偏离警报'
    },
    'time': {
        'en': 'Time',
        'zh': '时间'
    },
    'strike': {
        'en': 'Strike',
        'zh': '执行价'
    },
    'deviation': {
        'en': 'Deviation',
        'zh': '偏离'
    },
    'type': {
        'en': 'Type',
        'zh': '类型'
    },
    'trigger': {
        'en': 'Trigger',
        'zh': '触发条件'
    },
    'action': {
        'en': 'Action',
        'zh': '操作'
    },
    'deviation_volume_premium_chart': {
        'en': 'Deviation, Volume Change and Premium Change',
        'zh': '偏离率、成交量变化和权利金变化'
    },
    'deviation_data': {
        'en': 'Deviation Data',
        'zh': '偏离数据'
    },
    'export_csv': {
        'en': 'Export CSV',
        'zh': '导出CSV'
    },
    'market_price': {
        'en': 'Market Price',
        'zh': '市场价'
    },
    'expiration': {
        'en': 'Expiration',
        'zh': '到期日'
    },
    'volume': {
        'en': 'Volume',
        'zh': '成交量'
    },
    'volume_change': {
        'en': 'Volume Change',
        'zh': '成交量变化'
    },
    'premium': {
        'en': 'Premium',
        'zh': '权利金'
    },
    'premium_change': {
        'en': 'Premium Change',
        'zh': '权利金变化'
    },
    'market_change': {
        'en': 'Market Change',
        'zh': '市场价变化'
    },
    'status': {
        'en': 'Status',
        'zh': '状态'
    },
    'normal': {
        'en': 'Normal',
        'zh': '正常'
    },
    'exchange_comparison': {
        'en': 'Exchange Comparison',
        'zh': '交易所比较'
    },
    'put_call_ratio_comparison': {
        'en': 'Put/Call Ratio Comparison',
        'zh': '看跌/看涨比率比较'
    },
    'volume_distribution': {
        'en': 'Volume Distribution',
        'zh': '成交量分布'
    },
    'premium_spread': {
        'en': 'Premium Spread',
        'zh': '期权溢价差异'
    },
    'exchange': {
        'en': 'Exchange',
        'zh': '交易所'
    },
    'option_type': {
        'en': 'Option Type',
        'zh': '期权类型'
    },
    # 统计和趋势分析相关
    'trend_analysis': {
        'en': 'Trend Analysis',
        'zh': '趋势分析'
    },
    'showing_trends_over_time': {
        'en': 'Showing trends over time',
        'zh': '显示随时间变化的趋势'
    },
    'trend_analysis_helps_predict_market_movements': {
        'en': 'This analysis helps identify patterns that may predict future market movements',
        'zh': '此分析有助于识别可能预测未来市场走势的模式'
    },
    'export_chart_data': {
        'en': 'Export Chart Data',
        'zh': '导出图表数据'
    },
    'volume_change_min': {
        'en': 'Min Volume Change',
        'zh': '最小成交量变化'
    },
    'all': {
        'en': 'All',
        'zh': '全部'
    },
    'anomaly_alerts': {
        'en': 'Anomaly Alerts',
        'zh': '异常警报'
    },
    'no_alerts': {
        'en': 'No alerts',
        'zh': '无警报'
    },
    'alert_type': {
        'en': 'Alert Type',
        'zh': '警报类型'
    },
    'trigger_condition': {
        'en': 'Trigger Condition',
        'zh': '触发条件'
    },
    'acknowledged': {
        'en': 'Acknowledged',
        'zh': '已确认'
    }
}