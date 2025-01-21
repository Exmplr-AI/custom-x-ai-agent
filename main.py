from twitter import Twitter
import time
from datetime import datetime, timedelta
import pytz
import logging
import sys
import os

# Use /tmp directory for logs in Heroku
LOG_FILE = '/tmp/app.log'
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'a').close()

# Configure logging to output to both file and stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Ensures logs go to Heroku logs
        logging.FileHandler(LOG_FILE, mode='a')  # Append to file for web display
    ]
)

# Log startup
logging.info("=== Starting $EXMPLR Agent with Web Logs ===")
logger = logging.getLogger(__name__)

async def main():
    try:
        # Initialize client
        logger.info("Initializing Twitter client...")
        client = Twitter()
        logger.info("$EXMPLR Agent initialized successfully")
        
        # Initial setup
        logger.info("Starting initial setup (1 minute wait)...")
        time.sleep(60)
        
        logger.info("Collecting initial mentions...")
        client.collect_initial_mention()
        logger.info("Initial mentions collected")
        
        # Track post timings
        central = pytz.timezone('America/Chicago')
        # Set last marketing post to 15 minutes ago for quick initial post
        last_marketing_post = datetime.now(central) - timedelta(minutes=15)
        last_weekly_post = datetime.now(central)
        logger.info(f"Initialized timing trackers at {last_marketing_post} (marketing post due in 15 minutes)")
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                current_time = datetime.now(central)
                logger.info(f"\n=== Starting cycle {cycle_count} at {current_time} ===")
                
                # Handle mentions
                logger.info("Checking for mentions...")
                client.make_reply_to_mention()
                logger.info("Mention check complete, sleeping 5 minutes")
                time.sleep(5*60)
                
                # News analysis (now async)
                logger.info("Starting news analysis...")
                await client.analyze_news()
                logger.info("News analysis complete, sleeping 10 minutes")
                time.sleep(10*60)
                
                # Marketing posts (every 3.5 hours, 6-7x daily)
                time_since_marketing = (current_time - last_marketing_post).total_seconds()
                logger.info(f"Time since last marketing post: {time_since_marketing/3600:.2f} hours")
                
                if time_since_marketing >= 3.5*60*60:  # 210 minutes
                    logger.info("Generating marketing post...")
                    marketing_content = client.gen_ai.generate_marketing_post()
                    if marketing_content != 'failed':
                        client.client.create_tweet(text=marketing_content)
                        logger.info("Posted marketing content successfully")
                        last_marketing_post = current_time
                    else:
                        logger.error("Marketing content generation failed")
                
                # Weekly research post (Wednesdays)
                if (current_time.weekday() == 2 and
                    (current_time - last_weekly_post).days >= 7):
                    logger.info("Generating weekly research post...")
                    await client.analyze_news(is_weekly=True)
                    last_weekly_post = current_time
                    logger.info("Weekly research post complete")
                
                logger.info("Cycle complete, sleeping 10 minutes")
                time.sleep(10*60)
                
            except Exception as e:
                logger.error(f"Error in main loop cycle {cycle_count}: {str(e)}")
                logger.error("Sleeping 1 hour before retry")
                time.sleep(60*60)
    
    except Exception as e:
        logger.critical(f"Critical error in main function: {str(e)}")
        raise

import asyncio

if __name__ == "__main__":
    logger.info("=== Starting $EXMPLR social media agent ===")
    asyncio.run(main())
