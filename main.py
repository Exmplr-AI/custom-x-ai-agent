from twitter import Twitter
import time
from datetime import datetime, timedelta
import pytz


def main():
    # Initialize client
    client = Twitter()
    print("Starting $EXMPLR Twitter Bot...")
    
    # Initial setup
    time.sleep(5*60)
    client.collect_initial_mention()
    
    # Track post timings
    central = pytz.timezone('America/Chicago')
    last_marketing_post = datetime.now(central)
    last_weekly_post = datetime.now(central)
    
    while True:
        try:
            current_time = datetime.now(central)
            
            # Handle mentions (existing functionality)
            client.make_reply_to_mention()
            time.sleep(20*60)
            
            # Regular news analysis (existing functionality)
            client.analyze_news()
            time.sleep(20*60)
            
            # Marketing posts (every 8 hours, 3x daily)
            if (current_time - last_marketing_post).total_seconds() >= 8*60*60:
                marketing_content = client.gen_ai.generate_marketing_post()
                if marketing_content != 'failed':
                    client.client.create_tweet(text=marketing_content)
                    print("Posted marketing content")
                    last_marketing_post = current_time
            
            # Weekly research post (Wednesdays)
            if (current_time.weekday() == 2 and  # Wednesday
                (current_time - last_weekly_post).days >= 7):
                # Use existing news analysis with weekly flag
                client.analyze_news(is_weekly=True)
                last_weekly_post = current_time
            
            time.sleep(10*60)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60*60)


if __name__ == "__main__":
    print("Starting $EXMPLR social media bot...")
    main()
