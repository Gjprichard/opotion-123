import os
from app import app, db
from services.data_service import DataService
from services.risk_service import RiskService
from services.deviation_monitor_service import DeviationMonitorService
from config import Config
from utils.logging_config import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# Create service instances for initialization
data_service = DataService()
risk_service = RiskService()
deviation_service = DeviationMonitorService()

# Import routes later in the file to avoid circular imports

def initialize_database():
    """
    Initialize the database with real data for each tracked symbol
    """
    try:
        # Initialize data for each tracked symbol
        for symbol in Config.TRACKED_SYMBOLS:
            logger.info(f"Initializing data for {symbol} from real exchange APIs...")
            
            # Fetch latest option data for the symbol
            success = data_service.fetch_and_store_option_data(symbol)
            
            if success:
                # Calculate risk indicators based on the new data
                risk_service.calculate_risk_indicators(symbol)
                # 计算期权执行价偏离指标
                deviation_service.calculate_deviation_metrics(symbol)
                logger.info(f"Successfully initialized data for {symbol}")
            else:
                logger.error(f"Failed to initialize data for {symbol} - please check API connections")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

# Initialize the database with data when the app starts
with app.app_context():
    # Check if data already exists
    from models import OptionData
    count = OptionData.query.count()
    if count == 0:
        logger.info("No data found in database. Initializing...")
        initialize_database()
    else:
        logger.info(f"Database already contains {count} option data records")
    
    # Import routes after database initialization to avoid circular imports
    import routes  # noqa: F401

if __name__ == "__main__":
    # Make sure to run the server so it's accessible externally
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
