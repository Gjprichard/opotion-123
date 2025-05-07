from flask import render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
from sqlalchemy import func

from app import app, db
from models import OptionData, RiskIndicator, Alert, AlertThreshold, ScenarioAnalysis, StrikeDeviationMonitor, DeviationAlert, ApiCredential, SystemSetting
from config import Config
from main import data_service, risk_service, deviation_service
from services.alert_service import get_active_alerts, acknowledge_alert, update_alert_threshold
from services.exchange_api_ccxt import set_api_credentials, get_underlying_price, test_connection
from translations import translations

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # 获取时间周期参数，默认为15m
    time_period = request.args.get('time_period', '15m')
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    # 获取每个跟踪符号的最新风险指标
    latest_risk = {}
    for symbol in Config.TRACKED_SYMBOLS:
        indicator = RiskIndicator.query.filter_by(
            symbol=symbol,
            time_period=time_period
        ).order_by(RiskIndicator.timestamp.desc()).first()
        
        if indicator:
            latest_risk[symbol] = indicator
    
    # 获取活跃警报（未确认的）
    alerts = Alert.query.filter_by(
        is_acknowledged=False,
        time_period=time_period
    ).order_by(Alert.timestamp.desc()).limit(10).all()
    
    # 获取最新期权数据摘要
    latest_data_time = db.session.query(func.max(OptionData.timestamp)).scalar()
    options_count = OptionData.query.filter(
        OptionData.timestamp > (datetime.utcnow() - timedelta(days=1))
    ).count()
    
    return render_template('dashboard.html', 
                           latest_risk=latest_risk,
                           alerts=alerts,
                           latest_data_time=latest_data_time,
                           options_count=options_count,
                           symbols=Config.TRACKED_SYMBOLS,
                           time_periods=Config.TIME_PERIODS,
                           current_time_period=time_period)

@app.route('/api/dashboard/data')
def dashboard_data():
    try:
        symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
        days = int(request.args.get('days', 30))
        time_period = request.args.get('time_period', '15m')
        
        # 确保时间周期有效
        if time_period not in Config.TIME_PERIODS:
            time_period = '15m'
        
        app.logger.info(f"Fetching dashboard data for symbol={symbol}, days={days}, time_period={time_period}")
        
        # 使用RiskService获取历史风险指标
        risk_indicators = risk_service.get_historical_risk_indicators(symbol, time_period, days)
        
        app.logger.info(f"Found {len(risk_indicators)} risk indicator records for {symbol} ({time_period})")
        
        if not risk_indicators:
            # 如果没有找到数据，返回空结果
            return jsonify({
                'timestamps': [],
                'volaxivity': [],
                'volatility_skew': [],
                'put_call_ratio': [],
                'reflexivity_indicator': [],
                'thresholds': {},
                'time_period': time_period
            })
        
        # 从风险指标字典提取数据
        timestamps = [r.get('timestamp', '') for r in risk_indicators]
        volaxivity = [r.get('volaxivity', None) for r in risk_indicators]
        volatility_skew = [r.get('volatility_skew', None) for r in risk_indicators]
        put_call_ratio = [r.get('put_call_ratio', None) for r in risk_indicators]
        reflexivity = [r.get('reflexivity_indicator', None) for r in risk_indicators]
        
        # 获取当前时间周期的阈值设置
        thresholds = {}
        for indicator_name, periods in Config.DEFAULT_ALERT_THRESHOLDS.items():
            if time_period in periods:
                thresholds[indicator_name] = periods[time_period]
        
        return jsonify({
            'timestamps': timestamps,
            'volaxivity': volaxivity,
            'volatility_skew': volatility_skew,
            'put_call_ratio': put_call_ratio,
            'reflexivity_indicator': reflexivity,
            'thresholds': thresholds,
            'time_period': time_period
        })
    except Exception as e:
        app.logger.error(f"Error in dashboard_data: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while fetching dashboard data',
            'message': str(e)
        }), 500

@app.route('/alerts')
def alerts_view():
    # 获取时间周期参数，默认为15m
    time_period = request.args.get('time_period', '15m')
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    # Get all alerts, including acknowledged ones (filtered by time_period)
    all_alerts = Alert.query.filter_by(time_period=time_period).order_by(Alert.timestamp.desc()).limit(100).all()
    
    # Get current alert thresholds for this time period
    thresholds = AlertThreshold.query.filter_by(time_period=time_period).all()
    threshold_dict = {t.indicator: t for t in thresholds}
    
    return render_template('alerts.html', 
                           alerts=all_alerts, 
                           thresholds=threshold_dict,
                           default_thresholds=Config.DEFAULT_ALERT_THRESHOLDS,
                           time_periods=Config.TIME_PERIODS,
                           current_time_period=time_period)

@app.route('/api/alerts/acknowledge', methods=['POST'])
def acknowledge_alert_api():
    alert_id = request.json.get('alert_id')
    
    if not alert_id:
        return jsonify({'success': False, 'message': 'Alert ID is required'}), 400
    
    success = acknowledge_alert(alert_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Alert not found'}), 404

@app.route('/api/alerts/threshold', methods=['POST'])
def update_threshold():
    indicator = request.json.get('indicator')
    time_period = request.json.get('time_period', '15m')
    attention = float(request.json.get('attention'))
    warning = float(request.json.get('warning'))
    severe = float(request.json.get('severe'))
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    if not all([indicator, attention, warning, severe]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    success = update_alert_threshold(indicator, time_period, attention, warning, severe)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Error updating threshold'}), 500

@app.route('/historical')
def historical():
    symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
    option_type = request.args.get('type', 'call')
    days = int(request.args.get('days', 30))
    time_period = request.args.get('time_period', '15m')
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    # Get historical option data
    from_date = datetime.utcnow() - timedelta(days=days)
    options = OptionData.query.filter(
        OptionData.symbol == symbol,
        OptionData.option_type == option_type,
        OptionData.timestamp > from_date
    ).order_by(OptionData.timestamp.desc(), OptionData.strike_price).limit(1000).all()
    
    # Get expiration dates for the filter
    expirations = db.session.query(OptionData.expiration_date).filter(
        OptionData.symbol == symbol
    ).distinct().order_by(OptionData.expiration_date).all()
    
    return render_template('historical.html', 
                           options=options, 
                           symbol=symbol,
                           option_type=option_type,
                           days=days,
                           time_periods=Config.TIME_PERIODS,
                           current_time_period=time_period,
                           symbols=Config.TRACKED_SYMBOLS,
                           expirations=[exp[0] for exp in expirations])

@app.route('/api/historical/data')
def historical_data():
    symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
    option_type = request.args.get('type', 'call')
    expiration = request.args.get('expiration')
    strike = request.args.get('strike')
    
    # Build query based on provided filters
    query = OptionData.query.filter(OptionData.symbol == symbol)
    
    if option_type:
        query = query.filter(OptionData.option_type == option_type)
    
    if expiration:
        try:
            exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            query = query.filter(OptionData.expiration_date == exp_date)
        except ValueError:
            pass
    
    if strike:
        try:
            strike_price = float(strike)
            query = query.filter(OptionData.strike_price == strike_price)
        except ValueError:
            pass
    
    # Get the data
    options = query.order_by(OptionData.timestamp.desc()).limit(1000).all()
    
    # Format the data for chart.js
    result = []
    for opt in options:
        result.append({
            'timestamp': opt.timestamp.strftime('%Y-%m-%d %H:%M'),
            'strike': opt.strike_price,
            'price': opt.option_price,
            'iv': opt.implied_volatility,
            'delta': opt.delta,
            'gamma': opt.gamma,
            'theta': opt.theta,
            'vega': opt.vega,
            'underlying': opt.underlying_price
        })
    
    return jsonify(result)

@app.route('/scenario')
def scenario():
    # Get saved scenarios
    scenarios = ScenarioAnalysis.query.order_by(ScenarioAnalysis.created_at.desc()).all()
    
    return render_template('scenario.html', 
                           scenarios=scenarios,
                           symbols=Config.TRACKED_SYMBOLS)

@app.route('/api/scenario/run', methods=['POST'])
def run_scenario():
    scenario_data = request.json
    
    # Validate inputs
    required_fields = ['name', 'symbol', 'price_change', 'volatility_change', 'time_horizon']
    for field in required_fields:
        if field not in scenario_data:
            return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
    
    # Run the scenario analysis using risk_service
    result = risk_service.run_scenario_analysis(
        scenario_data['name'],
        scenario_data['symbol'],
        float(scenario_data['price_change']),
        float(scenario_data['volatility_change']),
        int(scenario_data['time_horizon']),
        scenario_data.get('description', '')
    )
    
    if result:
        return jsonify({
            'success': True,
            'scenario': {
                'id': result.id,
                'name': result.name,
                'symbol': result.symbol,
                'created_at': result.created_at.strftime('%Y-%m-%d %H:%M'),
                'price_change': result.price_change,
                'volatility_change': result.volatility_change,
                'time_horizon': result.time_horizon,
                'estimated_pnl': result.estimated_pnl,
                'estimated_delta': result.estimated_delta,
                'estimated_gamma': result.estimated_gamma,
                'estimated_vega': result.estimated_vega,
                'estimated_theta': result.estimated_theta
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Error running scenario analysis'}), 500

@app.route('/api/scenario/delete/<int:scenario_id>', methods=['POST'])
def delete_scenario(scenario_id):
    scenario = ScenarioAnalysis.query.get(scenario_id)
    
    if scenario:
        db.session.delete(scenario)
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Scenario not found'}), 404

@app.route('/settings')
def settings():
    time_period = request.args.get('time_period', '15m')
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    # 获取当前时间周期的警报阈值
    thresholds = AlertThreshold.query.filter_by(time_period=time_period).all()
    threshold_dict = {t.indicator: t for t in thresholds}
    
    # 获取API凭证（如果存在）
    api_credentials = ApiCredential.query.filter_by(api_name='deribit', is_active=True).first()
    
    # 检查是否启用实时数据
    use_real_data_setting = SystemSetting.query.filter_by(setting_name='use_real_data').first()
    use_real_data = use_real_data_setting.get_typed_value() if use_real_data_setting else False
    
    return render_template('settings.html', 
                           thresholds=threshold_dict,
                           default_thresholds=Config.DEFAULT_ALERT_THRESHOLDS,
                           time_periods=Config.TIME_PERIODS,
                           current_time_period=time_period,
                           api_credentials=api_credentials,
                           use_real_data=use_real_data,
                           config=Config)

@app.route('/api/data/refresh', methods=['POST'])
def refresh_data():
    symbol = request.json.get('symbol')
    
    if not symbol:
        return jsonify({'success': False, 'message': 'Symbol is required'}), 400
    
    # 使用DataService获取最新数据
    success = data_service.fetch_and_store_option_data(symbol)
    
    if success:
        # 使用RiskService计算风险指标
        risk_result = risk_service.calculate_risk_indicators(symbol)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Error fetching option data'}), 500

@app.route('/deviation_monitor')
def deviation_monitor():
    """期权执行价偏离监控页面"""
    symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
    time_period = request.args.get('time_period', '15m')
    anomaly_only = request.args.get('anomaly_only', 'false').lower() == 'true'
    days = int(request.args.get('days', 7))
    exchange = request.args.get('exchange', 'deribit')
    option_type = request.args.get('option_type', '')  # 'call', 'put' 或空字符串表示所有
    volume_change_filter = float(request.args.get('volume_change_filter', 0))  # 成交量变化过滤器，默认0表示不过滤
    
    # 确保时间周期有效
    if time_period not in Config.TIME_PERIODS:
        time_period = '15m'
    
    # 获取偏离数据 - 现在返回包含统计信息的字典
    deviation_data = deviation_service.get_deviation_data(
        symbol=symbol,
        time_period=time_period,
        is_anomaly=True if anomaly_only else None,
        days=days,
        exchange=exchange,
        option_type=option_type if option_type else None,
        volume_change_filter=volume_change_filter if volume_change_filter > 0 else None
    )
    
    # 分离偏离数据和统计信息
    deviations = deviation_data.get('deviations', [])
    statistics = deviation_data.get('statistics', {})
    
    # 获取未确认的偏离警报
    active_alerts = deviation_service.get_deviation_alerts(
        symbol=symbol,
        exchange=exchange,
        time_period=time_period,
        acknowledged=False
    )
    
    # 获取所有可用的到期日期
    expiration_dates = db.session.query(OptionData.expiration_date).filter(
        OptionData.symbol == symbol
    ).distinct().order_by(OptionData.expiration_date).all()
    
    return render_template('deviation_monitor.html',
                          deviations=deviations,
                          statistics=statistics,
                          active_alerts=active_alerts,
                          symbol=symbol,
                          days=days,
                          anomaly_only=anomaly_only,
                          symbols=Config.TRACKED_SYMBOLS,
                          time_periods=Config.TIME_PERIODS,
                          current_time_period=time_period,
                          exchange=exchange,
                          option_type=option_type,
                          volume_change_filter=volume_change_filter,
                          expiration_dates=[exp[0] for exp in expiration_dates])

@app.route('/api/deviation/data')
def deviation_data_api():
    """获取期权执行价偏离数据API"""
    try:
        symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
        time_period = request.args.get('time_period', '15m')
        anomaly_only = request.args.get('anomaly_only', 'false').lower() == 'true'
        days = int(request.args.get('days', 7))
        exchange = request.args.get('exchange', 'deribit')
        option_type = request.args.get('option_type', '')  # 'call', 'put' 或空字符串表示所有
        volume_change_filter = float(request.args.get('volume_change_filter', 0))  # 成交量变化过滤器，默认0表示不过滤
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'  # 是否包含统计数据
        
        app.logger.info(f"API请求参数: symbol={symbol}, time_period={time_period}, exchange={exchange}, days={days}, "
              f"option_type={option_type}, volume_change_filter={volume_change_filter}, anomaly_only={anomaly_only}, include_stats={include_stats}")
        
        # 确保时间周期有效
        if time_period not in Config.TIME_PERIODS:
            time_period = '15m'
        
        # 使用DeviationMonitorService获取偏离数据和统计信息
        deviation_data = deviation_service.get_deviation_data(
            symbol=symbol,
            time_period=time_period,
            is_anomaly=True if anomaly_only else None,
            days=days,
            exchange=exchange,
            option_type=option_type if option_type else None,
            volume_change_filter=volume_change_filter if volume_change_filter > 0 else None
        )
        
        # 分离偏离数据和统计信息
        deviations = deviation_data.get('deviations', [])
        statistics = deviation_data.get('statistics', {})
        
        # 格式化偏离数据
        formatted_deviations = []
        for dev in deviations:
            formatted_deviations.append({
                'id': dev.id,
                'timestamp': dev.timestamp.strftime('%Y-%m-%d %H:%M'),
                'symbol': dev.symbol,
                'strike_price': dev.strike_price,
                'market_price': dev.market_price,
                'deviation_percent': dev.deviation_percent,
                'option_type': dev.option_type,
                'exchange': dev.exchange,
                'expiration_date': dev.expiration_date.strftime('%Y-%m-%d'),
                'volume': dev.volume,
                'volume_change_percent': dev.volume_change_percent,
                'premium': dev.premium,
                'premium_change_percent': dev.premium_change_percent,
                'market_price_change_percent': dev.market_price_change_percent,
                'is_anomaly': dev.is_anomaly,
                'anomaly_level': dev.anomaly_level
            })
        
        # 如果客户端请求包含统计数据，则返回完整结果
        if include_stats:
            result = {
                'deviations': formatted_deviations,
                'statistics': statistics
            }
        else:
            # 否则只返回偏离数据
            result = formatted_deviations
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in deviation_data_api: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while fetching deviation data',
            'message': str(e)
        }), 500

@app.route('/api/deviation/alerts')
def deviation_alerts_api():
    """获取期权执行价偏离警报API"""
    try:
        symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
        time_period = request.args.get('time_period', '15m')
        acknowledged = request.args.get('acknowledged')
        exchange = request.args.get('exchange', 'deribit')
        option_type = request.args.get('option_type', '')  # 'call', 'put' 或空字符串表示所有
        
        if acknowledged is not None:
            acknowledged = acknowledged.lower() == 'true'
        
        # 确保时间周期有效
        if time_period not in Config.TIME_PERIODS:
            time_period = '15m'
        
        # 使用DeviationMonitorService获取偏离警报
        alerts = deviation_service.get_deviation_alerts(
            symbol=symbol,
            time_period=time_period,
            exchange=exchange,
            option_type=option_type if option_type else None,
            acknowledged=acknowledged
        )
        
        # 格式化数据
        result = []
        for alert in alerts:
            result.append({
                'id': alert.id,
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M'),
                'symbol': alert.symbol,
                'strike_price': alert.strike_price,
                'market_price': alert.market_price,
                'deviation_percent': alert.deviation_percent,
                'option_type': alert.option_type,
                'exchange': alert.exchange,
                'alert_type': alert.alert_type,
                'message': alert.message,
                'trigger_condition': alert.trigger_condition,
                'volume_change': alert.volume_change,
                'premium_change': alert.premium_change,
                'price_change': alert.price_change,
                'is_acknowledged': alert.is_acknowledged
            })
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in deviation_alerts_api: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while fetching deviation alerts',
            'message': str(e)
        }), 500

@app.route('/api/deviation/acknowledge', methods=['POST'])
def acknowledge_deviation_alert_api():
    """确认期权执行价偏离警报API"""
    alert_id = request.json.get('alert_id')
    
    if not alert_id:
        return jsonify({'success': False, 'message': 'Alert ID is required'}), 400
    
    # 使用DeviationMonitorService确认警报
    success = deviation_service.acknowledge_alert(alert_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Alert not found'}), 404
        
@app.route('/api/deviation/volume-analysis')
def deviation_volume_analysis_api():
    """获取期权执行价偏离监控的多空成交量分析数据API"""
    try:
        symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
        time_period = request.args.get('time_period', '15m')
        days = int(request.args.get('days', 7))
        include_history = request.args.get('include_history', 'true').lower() == 'true'
        
        app.logger.info(f"Volume analysis API请求参数: symbol={symbol}, time_period={time_period}, "
                       f"days={days}, include_history={include_history}")
        
        # 确保时间周期有效
        if time_period not in Config.TIME_PERIODS:
            time_period = '15m'
            
        # 限制返回的历史数据数量，以提高性能
        max_history_days = 10
        if days > max_history_days:
            app.logger.info(f"请求天数 {days} 超过最大历史天数 {max_history_days}，将限制为 {max_history_days}")
            days = max_history_days
        
        # 使用DeviationMonitorService获取成交量分析数据
        volume_data = deviation_service.get_call_put_volume_analysis(
            symbol=symbol,
            time_period=time_period,
            days=days,
            include_history=include_history
        )
        
        # 增强调试日志以检查API返回数据结构
        app.logger.info(f"Volume analysis API结果数据结构: {type(volume_data)}")
        
        if volume_data:
            # 记录主要数据结构的键
            app.logger.info(f"Volume data keys: {list(volume_data.keys() if isinstance(volume_data, dict) else [])}")
            
            # 记录exchange_data数据的结构
            if isinstance(volume_data, dict) and 'exchange_data' in volume_data:
                app.logger.info(f"Exchange data keys: {list(volume_data['exchange_data'].keys() if volume_data['exchange_data'] else [])}")
            
            # 记录history数据的结构
            if isinstance(volume_data, dict) and 'history' in volume_data:
                history_count = len(volume_data['history']) if volume_data['history'] else 0
                app.logger.info(f"History data entries: {history_count}")
                if history_count > 0:
                    # 检查第一个条目的结构
                    first_entry = volume_data['history'][0]
                    app.logger.info(f"First history entry keys: {list(first_entry.keys() if isinstance(first_entry, dict) else [])}")
        
        # 确保数据结构完整
        if not volume_data or not isinstance(volume_data, dict):
            app.logger.warning("返回的volume_data为空或不是字典类型")
            volume_data = create_default_volume_data()
            
        # 确保各个交易所数据存在
        if 'exchange_data' not in volume_data or not volume_data['exchange_data']:
            app.logger.warning("volume_data中没有exchange_data字段或为空")
            volume_data['exchange_data'] = {
                'deribit': {
                    'call_volume': 0,
                    'put_volume': 0,
                    'ratio': 1.0,
                    'anomaly_calls': 0,
                    'anomaly_puts': 0
                },
                'binance': {
                    'call_volume': 0,
                    'put_volume': 0,
                    'ratio': 1.0,
                    'anomaly_calls': 0,
                    'anomaly_puts': 0
                },
                'okx': {
                    'call_volume': 0,
                    'put_volume': 0,
                    'ratio': 1.0,
                    'anomaly_calls': 0,
                    'anomaly_puts': 0
                }
            }
            
        # 确保历史数据存在
        if include_history and ('history' not in volume_data or not volume_data['history']):
            app.logger.warning("请求包含历史数据但volume_data中没有history字段或为空")
            volume_data['history'] = [{
                'timestamp': 'N/A',
                'call_put_ratio': 1.0,
                'call_volume': 0,
                'put_volume': 0,
                'market_price': 0
            }]
            
        # 记录最终响应结构
        app.logger.info(f"Final volume analysis API响应结构: call_put_ratio存在: {'call_put_ratio' in volume_data}, "
                       f"exchange_data存在: {'exchange_data' in volume_data}, "
                       f"history存在: {'history' in volume_data}")
        
        return jsonify(volume_data)
    except Exception as e:
        app.logger.error(f"Error in deviation_volume_analysis_api: {str(e)}", exc_info=True)
        # 返回默认数据结构，避免客户端错误
        return jsonify(create_default_volume_data())

def create_default_volume_data():
    """创建默认的多空成交量分析数据结构 - 只在API获取数据失败时使用"""
    return {
        'call_put_ratio': 1.0,
        'volume_stats': {
            'total_volume': 0,
            'call_volume': 0,
            'put_volume': 0,
            'call_volume_percent': 50,
            'put_volume_percent': 50,
            'volume_change_24h': 0,
            'call_volume_change': 0,
            'put_volume_change': 0
        },
        'exchange_data': {
            'deribit': {
                'call_volume': 0,
                'put_volume': 0,
                'ratio': 1.0,
                'anomaly_calls': 0,
                'anomaly_puts': 0
            },
            'binance': {
                'call_volume': 0,
                'put_volume': 0,
                'ratio': 1.0,
                'anomaly_calls': 0,
                'anomaly_puts': 0
            },
            'okx': {
                'call_volume': 0,
                'put_volume': 0,
                'ratio': 1.0,
                'anomaly_calls': 0,
                'anomaly_puts': 0
            }
        },
        'anomaly_stats': {
            'total_anomalies': 0,
            'call_anomalies': 0,
            'put_anomalies': 0,
            'alert_level': 'normal',
            'alert_trigger': '数据获取失败'
        },
        'history': [
            {
                'timestamp': 'N/A',
                'call_put_ratio': 1.0,
                'call_volume': 0,
                'put_volume': 0,
                'market_price': 0
            }
        ]
    }

@app.route('/language/<lang>')
def set_language(lang):
    """Set the language preference"""
    if lang in Config.LANGUAGES:
        session['language'] = lang
        return redirect(request.referrer or url_for('dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/api/settings/api', methods=['POST'])
def save_api_settings():
    """保存API设置"""
    try:
        api_key = request.json.get('api_key', '')
        api_secret = request.json.get('api_secret', '')
        
        # 保存Deribit API凭证
        if api_key and api_secret:
            # 查询现有凭证
            api_credential = ApiCredential.query.filter_by(api_name='deribit').first()
            
            if api_credential:
                # 更新现有凭证
                api_credential.api_key = api_key
                api_credential.api_secret = api_secret
                api_credential.is_active = True
            else:
                # 创建新凭证
                api_credential = ApiCredential(
                    api_name='deribit',
                    api_key=api_key,
                    api_secret=api_secret,
                    is_active=True
                )
                db.session.add(api_credential)
            
            # 将凭证应用到API客户端
            set_api_credentials(api_key, api_secret)
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error saving API settings: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error saving API settings: {str(e)}'
        }), 500

@app.route('/api/settings/test-api', methods=['POST'])
def test_api_connection():
    """测试API连接"""
    try:
        api_key = request.json.get('api_key', '')
        api_secret = request.json.get('api_secret', '')
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'message': 'API key and secret are required'
            }), 400
        
        # 暂时设置API凭证用于测试
        set_api_credentials(api_key, api_secret)
        
        # 使用CCXT API测试连接
        success, message = test_connection()
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    
    except Exception as e:
        app.logger.error(f"Error testing API connection: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error testing API connection: {str(e)}'
        }), 500

@app.context_processor
def inject_language():
    """Inject language settings into all templates"""
    lang = session.get('language', Config.DEFAULT_LANGUAGE)
    
    def translate(key):
        """Translate a key based on current language"""
        if key.lower() in translations:
            return translations[key.lower()].get(lang, key)
        return key
    
    return {
        'current_language': lang,
        'languages': Config.LANGUAGES,
        't': translate  # Adding translation function to template context
    }
