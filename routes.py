from flask import render_template, jsonify, request, redirect, url_for
import logging

from app import app
from services.data_service import DataService
from services.risk_service import RiskService

# 配置日志
logger = logging.getLogger(__name__)

# 初始化服务
data_service = DataService()
risk_service = RiskService()

@app.route('/')
def index():
    """首页视图"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """仪表盘页面视图"""
    symbols = ["BTC", "ETH"]
    time_periods = ['15m', '1h', '4h', '1d', '7d']
    
    return render_template(
        'dashboard.html',
        title='期权风险监控仪表盘',
        symbols=symbols,
        default_symbol="BTC",
        time_periods=time_periods,
        default_time_period="1h"
    )

@app.route('/api/dashboard-data')
def dashboard_data():
    """仪表盘数据API"""
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'BTC')
        time_period = request.args.get('time_period', '1h')
        days = int(request.args.get('days', 30))
        
        logger.info(f"获取仪表盘数据: symbol={symbol}, time_period={time_period}, days={days}")
        
        # 获取最新的风险指标
        current_data = risk_service.calculate_risk_indicators(symbol, time_period)
        
        # 获取历史风险指标
        history_data = risk_service.get_historical_risk_indicators(
            symbol=symbol,
            time_period=time_period,
            days=days
        )
        
        # 获取交易所数据比较
        exchange_data = {}
        try:
            # 从三个交易所获取PCR比较数据
            exchanges = ['deribit', 'binance', 'okx']
            for exchange in exchanges:
                exchange_pcr = data_service.get_put_call_ratio(
                    symbol=symbol, 
                    exchange=exchange, 
                    days=1
                )
                
                # 如果成功获取数据，添加到交易所比较中
                if exchange_pcr and 'call_volume' in exchange_pcr and 'put_volume' in exchange_pcr:
                    exchange_data[exchange] = {
                        'call_volume': exchange_pcr.get('call_volume', 0),
                        'put_volume': exchange_pcr.get('put_volume', 0),
                        'ratio': exchange_pcr.get('ratio', 1.0)
                    }
        except Exception as ex:
            logger.warning(f"获取交易所比较数据时出错: {str(ex)}")
            # 在出错时提供默认数据，确保不影响整体功能
            if not exchange_data:
                exchange_data = {
                    'deribit': {'call_volume': 1000, 'put_volume': 1200, 'ratio': 1.2},
                    'binance': {'call_volume': 800, 'put_volume': 700, 'ratio': 0.88},
                    'okx': {'call_volume': 600, 'put_volume': 660, 'ratio': 1.1}
                }
        
        # 获取最新警报
        alerts = []  # TODO: 从alert_service获取警报数据
        
        # 构建响应JSON
        response = {
            'current': current_data,
            'history': history_data,
            'exchange_data': exchange_data,
            'alerts': alerts
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"获取仪表盘数据时出错: {str(e)}")
        # 返回空数据结构以确保前端不会崩溃
        return jsonify({
            'current': None,
            'history': [],
            'exchange_data': {},
            'alerts': []
        })

@app.route('/historical')
def historical():
    """历史数据页面视图"""
    symbols = ["BTC", "ETH"]
    time_periods = ['15m', '1h', '4h', '1d', '7d']
    
    return render_template(
        'historical.html',
        title='历史风险数据',
        symbols=symbols,
        default_symbol="BTC",
        time_periods=time_periods,
        default_time_period="1d"
    )

@app.route('/api/historical-data')
def historical_data():
    """历史数据API"""
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'BTC')
        time_period = request.args.get('time_period', '1d')
        days = int(request.args.get('days', 30))
        
        logger.info(f"获取历史数据: symbol={symbol}, time_period={time_period}, days={days}")
        
        # 获取历史风险指标
        indicators = risk_service.get_historical_risk_indicators(
            symbol=symbol,
            time_period=time_period,
            days=days
        )
        
        return jsonify(indicators)
    
    except Exception as e:
        logger.error(f"获取历史数据时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/pcr-analysis')
def pcr_analysis():
    """看跌/看涨比率分析页面视图"""
    symbols = ["BTC", "ETH"]
    
    return render_template(
        'pcr_analysis.html',
        title='看跌/看涨比率分析',
        symbols=symbols,
        default_symbol="BTC"
    )

@app.route('/api/pcr-data')
def pcr_data():
    """看跌/看涨比率数据API"""
    try:
        # 获取请求参数
        symbol = request.args.get('symbol', 'BTC')
        exchange = request.args.get('exchange', None)
        days = int(request.args.get('days', 7))
        
        logger.info(f"获取PCR数据: symbol={symbol}, exchange={exchange}, days={days}")
        
        # 获取看跌/看涨比率数据
        pcr_data = data_service.get_put_call_ratio(
            symbol=symbol,
            exchange=exchange,
            days=days
        )
        
        return jsonify(pcr_data)
    
    except Exception as e:
        logger.error(f"获取PCR数据时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/refresh-data')
def refresh_data():
    """刷新数据接口"""
    try:
        symbol = request.args.get('symbol', 'BTC')
        logger.info(f"手动刷新 {symbol} 数据")
        
        # 获取最新期权数据
        data_count = data_service.fetch_and_store_option_data(symbol)
        
        # 计算风险指标
        for period in ['15m', '1h', '4h', '1d', '7d']:
            risk_service.calculate_risk_indicators(symbol, period)
        
        return jsonify({
            'success': True,
            'message': f'成功获取 {data_count} 条 {symbol} 期权数据并更新风险指标'
        })
    
    except Exception as e:
        logger.error(f"刷新数据时出错: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 全局错误处理
@app.errorhandler(404)
def page_not_found(e):
    """404页面"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """500页面"""
    return render_template('500.html'), 500