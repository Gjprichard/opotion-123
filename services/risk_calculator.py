import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func

from app import db
from models import OptionData, RiskIndicator, ScenarioAnalysis
from services.alert_service import check_alert_thresholds
from config import Config

logger = logging.getLogger(__name__)

def calculate_risk_indicators(symbol):
    """
    Calculate various risk indicators based on option market data
    Implements the reflexivity theory to identify feedback loops
    """
    try:
        logger.info(f"Calculating risk indicators for {symbol}")
        
        # Get the latest timestamp with data available
        latest_time = db.session.query(func.max(OptionData.timestamp)).filter(
            OptionData.symbol == symbol
        ).scalar()
        
        if not latest_time:
            logger.warning(f"No option data found for {symbol}")
            return False
        
        # Get data from this timestamp
        options = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp == latest_time
        ).all()
        
        if not options:
            logger.warning(f"No option data found for {symbol} at {latest_time}")
            return False
        
        # Convert to pandas DataFrame for easier calculations
        df = pd.DataFrame([{
            'strike': opt.strike_price,
            'option_type': opt.option_type,
            'price': opt.option_price,
            'iv': opt.implied_volatility,
            'delta': opt.delta,
            'gamma': opt.gamma,
            'vega': opt.vega,
            'theta': opt.theta,
            'volume': opt.volume,
            'open_interest': opt.open_interest,
            'underlying': opt.underlying_price
        } for opt in options])
        
        # Calculate key risk indicators
        volaxivity = calculate_volaxivity(df)
        volatility_skew = calculate_volatility_skew(df)
        put_call_ratio = calculate_put_call_ratio(df)
        reflexivity = calculate_reflexivity_indicator(df)
        market_sentiment = determine_market_sentiment(volaxivity, put_call_ratio, reflexivity)
        
        # Create or update risk indicator record
        risk_indicator = RiskIndicator(
            symbol=symbol,
            timestamp=latest_time,
            volaxivity=volaxivity,
            volatility_skew=volatility_skew,
            put_call_ratio=put_call_ratio,
            market_sentiment=market_sentiment,
            reflexivity_indicator=reflexivity
        )
        
        db.session.add(risk_indicator)
        db.session.commit()
        
        # Check if any risk thresholds are crossed
        check_alert_thresholds(risk_indicator)
        
        logger.info(f"Calculated risk indicators for {symbol}: Volaxivity={volaxivity:.2f}, Skew={volatility_skew:.2f}, PCR={put_call_ratio:.2f}, Reflexivity={reflexivity:.2f}")
        return True
        
    except Exception as e:
        logger.error(f"Error calculating risk indicators: {str(e)}")
        db.session.rollback()
        return False

def calculate_volaxivity(df):
    """
    Calculate the Volaxivity indicator (custom volatility index)
    Higher values indicate higher market risk
    """
    # Get ATM options (closest to current price)
    underlying_price = df['underlying'].iloc[0]
    
    # Filter to near-the-money options
    atm_options = df[abs(df['strike'] - underlying_price) / underlying_price < 0.05]
    
    if atm_options.empty:
        # If no options are near ATM, use all options
        atm_options = df
    
    # Calculate weighted average IV using volume as weight
    if 'volume' in atm_options and atm_options['volume'].sum() > 0:
        weighted_iv = (atm_options['iv'] * atm_options['volume']).sum() / atm_options['volume'].sum()
    else:
        weighted_iv = atm_options['iv'].mean()
    
    # Calculate IV change rate compared to historical average (simulated)
    historical_iv_avg = 0.20  # This would normally be retrieved from historical data
    iv_change_rate = weighted_iv / historical_iv_avg - 1
    
    # Calculate option activity indicator (volume relative to open interest)
    if atm_options['open_interest'].sum() > 0:
        activity_ratio = atm_options['volume'].sum() / atm_options['open_interest'].sum()
    else:
        activity_ratio = 0
    
    # Calculate Volaxivity
    volaxivity = (weighted_iv * 100) * (1 + iv_change_rate) * (1 + min(activity_ratio, 1))
    
    return volaxivity

def calculate_volatility_skew(df):
    """
    Calculate volatility skew (difference between OTM put and call implied volatility)
    Higher values indicate more fear in the market
    """
    # Get the underlying price
    underlying_price = df['underlying'].iloc[0]
    
    # Find OTM puts (strike < price)
    otm_puts = df[(df['option_type'] == 'put') & (df['strike'] < underlying_price)]
    
    # Find OTM calls (strike > price)
    otm_calls = df[(df['option_type'] == 'call') & (df['strike'] > underlying_price)]
    
    if otm_puts.empty or otm_calls.empty:
        return 0
    
    # Calculate average IV for OTM puts and calls
    avg_put_iv = otm_puts['iv'].mean()
    avg_call_iv = otm_calls['iv'].mean()
    
    # Calculate skew (put IV - call IV)
    skew = avg_put_iv - avg_call_iv
    
    return skew

def calculate_put_call_ratio(df):
    """
    Calculate put-call ratio based on volume or open interest
    High values indicate bearish sentiment
    """
    # Get total put and call volume
    put_volume = df[df['option_type'] == 'put']['volume'].sum()
    call_volume = df[df['option_type'] == 'call']['volume'].sum()
    
    # Calculate put-call ratio
    if call_volume > 0:
        pcr = put_volume / call_volume
    else:
        pcr = 1.0  # Default to neutral if no call volume
    
    return pcr

def calculate_reflexivity_indicator(df):
    """
    Calculate reflexivity indicator based on market feedback loops
    Uses gamma exposure as a proxy for potential market feedback
    """
    # Get the underlying price
    underlying_price = df['underlying'].iloc[0]
    
    # Calculate total gamma exposure
    total_gamma = (df['gamma'] * df['open_interest']).sum()
    
    # Normalize by underlying price
    normalized_gamma = total_gamma / underlying_price
    
    # Calculate delta imbalance (call delta - put delta)
    call_delta = df[df['option_type'] == 'call']['delta'].sum()
    put_delta = abs(df[df['option_type'] == 'put']['delta'].sum())
    delta_imbalance = abs(call_delta - put_delta) / (call_delta + put_delta) if (call_delta + put_delta) > 0 else 0
    
    # Combine gamma exposure and delta imbalance for reflexivity indicator
    reflexivity = normalized_gamma * (1 + delta_imbalance)
    
    # Scale to a 0-1 range
    scaled_reflexivity = min(1.0, reflexivity / 0.1)  # 0.1 is a normalization factor
    
    return scaled_reflexivity

def determine_market_sentiment(volaxivity, put_call_ratio, reflexivity):
    """
    Determine market sentiment based on risk indicators
    Returns 'risk-on' or 'risk-off'
    """
    # Define thresholds
    volaxivity_threshold = 25
    pcr_threshold = 1.2
    reflexivity_threshold = 0.5
    
    # Count risk-off signals
    risk_off_signals = 0
    
    if volaxivity > volaxivity_threshold:
        risk_off_signals += 1
    
    if put_call_ratio > pcr_threshold:
        risk_off_signals += 1
    
    if reflexivity > reflexivity_threshold:
        risk_off_signals += 1
    
    # Determine sentiment based on majority of signals
    if risk_off_signals >= 2:
        return 'risk-off'
    else:
        return 'risk-on'

def run_scenario_analysis(name, symbol, price_change, volatility_change, time_horizon, description=''):
    """
    Run a scenario analysis for a given symbol with specified market changes
    Returns the created ScenarioAnalysis object
    """
    try:
        logger.info(f"Running scenario analysis '{name}' for {symbol}")
        
        # Get the latest option data for the symbol
        latest_time = db.session.query(func.max(OptionData.timestamp)).filter(
            OptionData.symbol == symbol
        ).scalar()
        
        if not latest_time:
            logger.warning(f"No option data found for {symbol}")
            return None
        
        options = OptionData.query.filter(
            OptionData.symbol == symbol,
            OptionData.timestamp == latest_time
        ).all()
        
        if not options:
            logger.warning(f"No option data found for {symbol} at {latest_time}")
            return None
        
        # Get current underlying price
        current_price = options[0].underlying_price
        
        # Calculate new price based on price change percentage
        new_price = current_price * (1 + price_change / 100)
        
        # Simulate the effect on option Greeks and P&L
        total_delta = 0
        total_gamma = 0
        total_vega = 0
        total_theta = 0
        estimated_pnl = 0
        
        for option in options:
            # Calculate price change effect
            price_effect = option.delta * (new_price - current_price)
            
            # Calculate volatility change effect (using vega)
            vol_effect = option.vega * volatility_change
            
            # Calculate time decay effect
            time_effect = option.theta * time_horizon
            
            # Calculate total P&L effect
            option_pnl = price_effect + vol_effect + time_effect
            estimated_pnl += option_pnl
            
            # Accumulate Greeks for the new scenario
            total_delta += option.delta
            total_gamma += option.gamma
            total_vega += option.vega
            total_theta += option.theta
        
        # Create and save the scenario analysis
        scenario = ScenarioAnalysis(
            name=name,
            description=description,
            symbol=symbol,
            created_at=datetime.utcnow(),
            price_change=price_change,
            volatility_change=volatility_change,
            time_horizon=time_horizon,
            estimated_pnl=estimated_pnl,
            estimated_delta=total_delta,
            estimated_gamma=total_gamma,
            estimated_vega=total_vega,
            estimated_theta=total_theta
        )
        
        db.session.add(scenario)
        db.session.commit()
        
        logger.info(f"Scenario analysis completed: Estimated P&L = {estimated_pnl:.2f}")
        return scenario
        
    except Exception as e:
        logger.error(f"Error running scenario analysis: {str(e)}")
        db.session.rollback()
        return None
