import logging
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_crypto_columns():
    """
    Add crypto-specific columns to RiskIndicator table
    """
    with app.app_context():
        try:
            logger.info("Beginning database migration to add crypto-specific columns...")
            
            # Check if columns already exist
            conn = db.engine.connect()
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'risk_indicator' 
                AND column_name = 'funding_rate'
            """))
            
            if result.fetchone():
                logger.info("Column 'funding_rate' already exists, skipping migration")
                return
                
            # Add columns
            conn.execute(text("""
                ALTER TABLE risk_indicator 
                ADD COLUMN funding_rate FLOAT,
                ADD COLUMN liquidation_risk FLOAT
            """))
            
            conn.commit()
            logger.info("Successfully added crypto-specific columns to RiskIndicator table")
        
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    add_crypto_columns()