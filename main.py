from app import app, db
import routes  # noqa: F401
from services.data_service import fetch_latest_option_data
from services.risk_calculator import calculate_risk_indicators
from config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database():
    """
    Initialize the database with some data for each tracked symbol
    """
    try:
        # Initialize data for each tracked symbol
        for symbol in Config.TRACKED_SYMBOLS:
            logger.info(f"Initializing data for {symbol}...")
            
            # Fetch latest option data for the symbol
            success = fetch_latest_option_data(symbol)
            
            if success:
                # Calculate risk indicators based on the new data
                calculate_risk_indicators(symbol)
                logger.info(f"Successfully initialized data for {symbol}")
            else:
                logger.error(f"Failed to initialize data for {symbol}")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
