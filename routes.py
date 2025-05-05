from flask import render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
from sqlalchemy import func

from app import app, db
from models import OptionData, RiskIndicator, Alert, AlertThreshold, ScenarioAnalysis
from config import Config
from services.data_service import fetch_latest_option_data, fetch_historical_data
from services.risk_calculator import calculate_risk_indicators, run_scenario_analysis
from services.alert_service import get_active_alerts, acknowledge_alert, update_alert_threshold
from translations import translations

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Get the latest risk indicators for tracked symbols
    latest_risk = {}
    for symbol in Config.TRACKED_SYMBOLS:
        indicator = RiskIndicator.query.filter_by(symbol=symbol).order_by(RiskIndicator.timestamp.desc()).first()
        if indicator:
            latest_risk[symbol] = indicator
    
    # Get active alerts
    alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.timestamp.desc()).limit(10).all()
    
    # Get latest option data summary
    latest_data_time = db.session.query(func.max(OptionData.timestamp)).scalar()
    options_count = OptionData.query.filter(OptionData.timestamp > (datetime.utcnow() - timedelta(days=1))).count()
    
    return render_template('dashboard.html', 
                           latest_risk=latest_risk,
                           alerts=alerts,
                           latest_data_time=latest_data_time,
                           options_count=options_count,
                           symbols=Config.TRACKED_SYMBOLS)

@app.route('/api/dashboard/data')
def dashboard_data():
    symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
    days = int(request.args.get('days', 7))
    
    # Get risk indicators for the past N days
    from_date = datetime.utcnow() - timedelta(days=days)
    risk_data = RiskIndicator.query.filter(
        RiskIndicator.symbol == symbol,
        RiskIndicator.timestamp > from_date
    ).order_by(RiskIndicator.timestamp).all()
    
    # Format the data for chart.js
    timestamps = [r.timestamp.strftime('%Y-%m-%d %H:%M') for r in risk_data]
    volaxivity = [r.volaxivity for r in risk_data]
    volatility_skew = [r.volatility_skew for r in risk_data]
    put_call_ratio = [r.put_call_ratio for r in risk_data]
    reflexivity = [r.reflexivity_indicator for r in risk_data]
    
    return jsonify({
        'timestamps': timestamps,
        'volaxivity': volaxivity,
        'volatility_skew': volatility_skew,
        'put_call_ratio': put_call_ratio,
        'reflexivity': reflexivity
    })

@app.route('/alerts')
def alerts_view():
    # Get all alerts, including acknowledged ones
    all_alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(100).all()
    
    # Get current alert thresholds
    thresholds = AlertThreshold.query.all()
    threshold_dict = {t.indicator: t for t in thresholds}
    
    return render_template('alerts.html', 
                           alerts=all_alerts, 
                           thresholds=threshold_dict,
                           default_thresholds=Config.DEFAULT_ALERT_THRESHOLDS)

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
    attention = float(request.json.get('attention'))
    warning = float(request.json.get('warning'))
    severe = float(request.json.get('severe'))
    
    if not all([indicator, attention, warning, severe]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    success = update_alert_threshold(indicator, attention, warning, severe)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Error updating threshold'}), 500

@app.route('/historical')
def historical():
    symbol = request.args.get('symbol', Config.TRACKED_SYMBOLS[0])
    option_type = request.args.get('type', 'call')
    days = int(request.args.get('days', 7))
    
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
    
    # Run the scenario analysis
    result = run_scenario_analysis(
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
    # Get current alert thresholds
    thresholds = AlertThreshold.query.all()
    threshold_dict = {t.indicator: t for t in thresholds}
    
    return render_template('settings.html', 
                           thresholds=threshold_dict,
                           default_thresholds=Config.DEFAULT_ALERT_THRESHOLDS)

@app.route('/api/data/refresh', methods=['POST'])
def refresh_data():
    symbol = request.json.get('symbol')
    
    if not symbol:
        return jsonify({'success': False, 'message': 'Symbol is required'}), 400
    
    # Fetch latest data
    success = fetch_latest_option_data(symbol)
    
    if success:
        # Calculate risk indicators based on new data
        calculate_risk_indicators(symbol)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Error fetching option data'}), 500

@app.route('/language/<lang>')
def set_language(lang):
    """Set the language preference"""
    if lang in Config.LANGUAGES:
        session['language'] = lang
        return redirect(request.referrer or url_for('dashboard'))
    return redirect(url_for('dashboard'))

@app.context_processor
def inject_language():
    """Inject language settings into all templates"""
    lang = session.get('language', Config.DEFAULT_LANGUAGE)
    return {
        'current_language': lang,
        'languages': Config.LANGUAGES
    }
