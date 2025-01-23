from twitter import Twitter
import time
from datetime import datetime, timedelta
import pytz
import logging
import sys
import os

# Configure logging to output to stdout for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensures logs go to Heroku logs
    ]
)

# Log startup
logging.info("=== Starting $EXMPLR Agent ===")
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
        # Set last news post to now to start fresh
        last_news_post = datetime.now(central)
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
                
                # News analysis (every 4 hours)
                time_since_news = (current_time - last_news_post).total_seconds()
                logger.info(f"Time since last news post: {time_since_news/3600:.2f} hours")
                
                if time_since_news >= 4*60*60:  # 240 minutes
                    logger.info("Starting news analysis...")
                    news_posted = await client.analyze_news()
                    if news_posted:
                        logger.info("News post successful, updating last news post time")
                        last_news_post = current_time
                    logger.info("News analysis complete, sleeping 10 minutes")
                    time.sleep(10*60)
                else:
                    logger.info("Skipping news analysis due to cooldown")
                
                # Marketing posts (every 3.5 hours, 6-7x daily)
                time_since_marketing = (current_time - last_marketing_post).total_seconds()
                logger.info(f"Time since last marketing post: {time_since_marketing/3600:.2f} hours")
                
                if time_since_marketing >= 3.5*60*60:  # 210 minutes
                    logger.info("=== Starting Marketing Post Generation ===")
                    logger.info(f"Content type selection and generation starting at {current_time}")
                    marketing_content = await client.gen_ai.generate_marketing_post()
                    if marketing_content and marketing_content != 'failed':
                        logger.info("Marketing content generated successfully")
                        logger.info(f"Content preview: {marketing_content[:100]}...")
                        client.client.create_tweet(text=marketing_content)
                        logger.info("Marketing content posted successfully")
                        last_marketing_post = current_time
                    else:
                        logger.error("Marketing content generation failed or returned empty")
                        logger.info("Will retry in next cycle")
                
                # Weekly research post (Wednesdays)
                is_wednesday = current_time.weekday() == 2
                days_since_last = (current_time - last_weekly_post).days
                logger.info(f"Weekly post check - Is Wednesday: {is_wednesday}, Days since last: {days_since_last}")
                
                if is_wednesday and days_since_last >= 7:
                    logger.info("=== Starting Weekly Research Post Generation ===")
                    logger.info(f"Weekly content generation starting at {current_time}")
                    await client.analyze_news(is_weekly=True)
                    last_weekly_post = current_time
                    logger.info("Weekly research post cycle complete")
                
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
