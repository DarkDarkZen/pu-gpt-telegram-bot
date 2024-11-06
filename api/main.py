import sys
import os
import logging

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bot import GPTBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Initialize and run bot in polling mode
        logger.info("Starting bot...")
        bot = GPTBot()
        bot.run()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise e 