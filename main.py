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

# Configure startup logging
logger = logging.getLogger(__name__)
logger.info("\n" + "="*50)
logger.info("INITIALIZING $EXMPLR AGENT")
logger.info("="*50 + "\n")

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
        # Set initial timings
        last_news_post = datetime.now(central)
        last_timeline_check = datetime.now(central)
        last_search_check = datetime.now(central)
        logger.info(f"Initialized timing trackers:")
        logger.info(f"- Marketing post due in 15 minutes")
        logger.info(f"- Timeline check due in 1 hour")
        logger.info(f"- Topic search due in 2 hours")
        logger.info(f"- News analysis due in 4 hours")
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                current_time = datetime.now(central)
                logger.info("\n" + "="*50)
                logger.info(f"CYCLE {cycle_count} - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("="*50)
                
                # Handle mentions
                logger.info("\n🔍 Checking for mentions...")
                mention_count = client.make_reply_to_mention()
                if mention_count > 0:
                    logger.info(f"✅ Processed {mention_count} mentions")
                else:
                    logger.info("ℹ️ No new mentions to process")
                logger.info("⏳ Sleeping 5 minutes after mention check")
                time.sleep(5*60)
                
                # Monitor timeline and interact (every hour)
                time_since_timeline = (current_time - last_timeline_check).total_seconds()
                time_until_timeline = max(0, 3600 - time_since_timeline)
                logger.info("\n📊 TIMELINE MONITORING STATUS")
                logger.info(f"⏱️ Timeline check frequency: Every 1 hour")
                logger.info(f"⌛ Time since last check: {time_since_timeline/3600:.1f} hours")
                logger.info(f"⏳ Time until next check: {time_until_timeline/60:.0f} minutes")
                
                if time_since_timeline >= 1*60*60:  # 60 minutes
                    logger.info("🔄 Starting timeline monitoring...")
                    timeline_interactions = await client.monitor_following_feed()
                    if timeline_interactions > 0:
                        logger.info(f"✅ Timeline monitoring complete: {timeline_interactions} successful interactions")
                    else:
                        logger.info("ℹ️ Timeline monitoring complete: No qualifying tweets found")
                    last_timeline_check = current_time
                else:
                    logger.info("⏳ Timeline check in cooldown")
                
                # Topic-based search and interactions (every 2 hours)
                time_since_search = (current_time - last_search_check).total_seconds()
                time_until_search = max(0, 7200 - time_since_search)
                logger.info("\n🔍 TOPIC SEARCH STATUS")
                logger.info(f"⏱️ Search frequency: Every 2 hours")
                logger.info(f"⌛ Time since last search: {time_since_search/3600:.1f} hours")
                logger.info(f"⏳ Time until next search: {time_until_search/60:.0f} minutes")
                
                if time_since_search >= 2*60*60:  # 120 minutes
                    logger.info("🔄 Starting topic-based tweet search...")
                    search_interactions = await client.search_and_interact()
                    if search_interactions > 0:
                        logger.info(f"✅ Topic search complete: {search_interactions} successful interactions")
                        logger.info("⏳ Sleeping 5 minutes after successful interactions")
                        time.sleep(5*60)
                    else:
                        logger.info("ℹ️ Topic search complete: No qualifying tweets found")
                    last_search_check = current_time
                else:
                    logger.info("⏳ Topic search in cooldown")
                
                # News analysis (every 4 hours)
                time_since_news = (current_time - last_news_post).total_seconds()
                time_until_news = max(0, 14400 - time_since_news)
                logger.info("\n📰 NEWS ANALYSIS STATUS")
                logger.info(f"⏱️ Analysis frequency: Every 4 hours")
                logger.info(f"⌛ Time since last analysis: {time_since_news/3600:.1f} hours")
                logger.info(f"⏳ Time until next analysis: {time_until_news/60:.0f} minutes")
                
                if time_since_news >= 4*60*60:  # 240 minutes
                    logger.info("🔄 Starting news article analysis...")
                    news_posted = await client.analyze_news()
                    if news_posted:
                        logger.info("✅ News post successful")
                        last_news_post = current_time
                        logger.info("⏳ Sleeping 10 minutes after successful post")
                        time.sleep(10*60)
                    else:
                        logger.info("ℹ️ No qualifying news articles found")
                else:
                    logger.info("⏳ News analysis in cooldown")
                
                # Marketing posts (initial: 15 mins, then every 3.5 hours)
                time_since_marketing = (current_time - last_marketing_post).total_seconds()
                is_initial_post = cycle_count <= 2  # Check if this is within first 2 cycles
                required_wait = 15*60 if is_initial_post else 3.5*60*60  # 15 mins for initial, 3.5 hrs after
                time_until_marketing = max(0, required_wait - time_since_marketing)
                
                logger.info("\n📢 MARKETING POST STATUS")
                logger.info(f"⏱️ Post frequency: {'First post in 15 minutes' if is_initial_post else 'Every 3.5 hours'}")
                logger.info(f"⌛ Time since last post: {time_since_marketing/3600:.1f} hours")
                logger.info(f"⏳ Time until next post: {time_until_marketing/60:.0f} minutes")
                
                if time_since_marketing >= required_wait:
                    logger.info("🔄 Starting marketing post generation...")
                    marketing_content = await client.gen_ai.generate_marketing_post()
                    if marketing_content and marketing_content != 'failed':
                        logger.info("✅ Marketing content generated")
                        logger.info("📝 Content preview:")
                        logger.info(f"   {marketing_content[:100]}...")
                        client.client.create_tweet(text=marketing_content)
                        logger.info("✅ Marketing content posted successfully")
                        last_marketing_post = current_time
                    else:
                        logger.error("❌ Marketing content generation failed")
                        logger.info("🔄 Will retry in next cycle")
                
                # Weekly research post (Wednesdays)
                is_wednesday = current_time.weekday() == 2
                days_since_last = (current_time - last_weekly_post).days
                days_until_next = (7 - days_since_last) if is_wednesday else (((9 - current_time.weekday()) % 7) + days_since_last)
                
                logger.info("\n📚 WEEKLY RESEARCH STATUS")
                logger.info(f"⏱️ Post frequency: Every Wednesday")
                logger.info(f"📅 Current day: {'Wednesday ✓' if is_wednesday else f'{current_time.strftime("%A")} ✗'}")
                logger.info(f"⌛ Days since last post: {days_since_last}")
                logger.info(f"⏳ Days until next post: {days_until_next}")
                
                if is_wednesday and days_since_last >= 7:
                    logger.info("🔄 Starting weekly research post generation...")
                    await client.analyze_news(is_weekly=True)
                    last_weekly_post = current_time
                    logger.info("✅ Weekly research post complete")
                
                logger.info("\n" + "="*50)
                logger.info("CYCLE COMPLETE - Sleeping 10 minutes")
                logger.info("="*50 + "\n")
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
