import logging
from .bot import GPTBot

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