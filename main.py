from twitter import Twitter
import time
from datetime import datetime, timedelta
import pytz
import logging
import sys
import os
import json

# Configure JSON formatter for structured logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Basic log record attributes
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
            
        return json.dumps(log_obj)

# Configure logging to output JSON to stderr for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Use stderr for Heroku logs
    ]
)

# Get the root logger and set the JSON formatter
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(JsonFormatter())

# Create logger for this module
logger = logging.getLogger(__name__)

# Log startup with extra fields
logger.info("Starting $EXMPLR Agent with Web Logs", 
    extra={'extra_fields': {
        'component': 'worker',
        'version': '1.0.0',
        'environment': os.environ.get('ENVIRONMENT', 'production')
    }}
)

async def main():
    try:
        # Initialize client
        logger.info("Initializing Twitter client...",
            extra={'extra_fields': {'action': 'init', 'service': 'twitter'}}
        )
        client = Twitter()
        logger.info("$EXMPLR Agent initialized successfully",
            extra={'extra_fields': {'action': 'init', 'status': 'success'}}
        )
        
        # Initial setup
        logger.info("Starting initial setup (1 minute wait)...",
            extra={'extra_fields': {'action': 'setup', 'wait_time': 60}}
        )
        time.sleep(60)
        
        logger.info("Collecting initial mentions...",
            extra={'extra_fields': {'action': 'collect_mentions', 'type': 'initial'}}
        )
        client.collect_initial_mention()
        logger.info("Initial mentions collected",
            extra={'extra_fields': {'action': 'collect_mentions', 'status': 'complete'}}
        )
        
        # Track post timings
        central = pytz.timezone('America/Chicago')
        # Set last marketing post to 15 minutes ago for quick initial post
        last_marketing_post = datetime.now(central) - timedelta(minutes=15)
        last_weekly_post = datetime.now(central)
        logger.info("Initialized timing trackers",
            extra={'extra_fields': {
                'action': 'init_timers',
                'last_marketing': last_marketing_post.isoformat(),
                'last_weekly': last_weekly_post.isoformat()
            }}
        )
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                current_time = datetime.now(central)
                logger.info("Starting cycle",
                    extra={'extra_fields': {
                        'cycle': cycle_count,
                        'timestamp': current_time.isoformat()
                    }}
                )
                
                # Handle mentions
                logger.info("Checking for mentions...",
                    extra={'extra_fields': {'action': 'check_mentions', 'cycle': cycle_count}}
                )
                client.make_reply_to_mention()
                logger.info("Mention check complete",
                    extra={'extra_fields': {
                        'action': 'check_mentions',
                        'status': 'complete',
                        'next_wait': 300
                    }}
                )
                time.sleep(5*60)
                
                # News analysis (now async)
                logger.info("Starting news analysis...",
                    extra={'extra_fields': {'action': 'analyze_news', 'cycle': cycle_count}}
                )
                await client.analyze_news()
                logger.info("News analysis complete",
                    extra={'extra_fields': {
                        'action': 'analyze_news',
                        'status': 'complete',
                        'next_wait': 600
                    }}
                )
                time.sleep(10*60)
                
                # Marketing posts (every 3.5 hours, 6-7x daily)
                time_since_marketing = (current_time - last_marketing_post).total_seconds()
                logger.info("Checking marketing post timing",
                    extra={'extra_fields': {
                        'action': 'check_marketing',
                        'hours_since_last': time_since_marketing/3600
                    }}
                )
                
                if time_since_marketing >= 3.5*60*60:  # 210 minutes
                    logger.info("Generating marketing post...",
                        extra={'extra_fields': {'action': 'marketing_post'}}
                    )
                    marketing_content = client.gen_ai.generate_marketing_post()
                    if marketing_content != 'failed':
                        client.client.create_tweet(text=marketing_content)
                        logger.info("Posted marketing content",
                            extra={'extra_fields': {
                                'action': 'marketing_post',
                                'status': 'success',
                                'content_length': len(marketing_content)
                            }}
                        )
                        last_marketing_post = current_time
                    else:
                        logger.error("Marketing content generation failed",
                            extra={'extra_fields': {
                                'action': 'marketing_post',
                                'status': 'failed',
                                'error': 'generation_failed'
                            }}
                        )
                
                # Weekly research post (Wednesdays)
                if (current_time.weekday() == 2 and
                    (current_time - last_weekly_post).days >= 7):
                    logger.info("Generating weekly research post...",
                        extra={'extra_fields': {'action': 'weekly_post'}}
                    )
                    await client.analyze_news(is_weekly=True)
                    last_weekly_post = current_time
                    logger.info("Weekly research post complete",
                        extra={'extra_fields': {
                            'action': 'weekly_post',
                            'status': 'complete'
                        }}
                    )
                
                logger.info("Cycle complete",
                    extra={'extra_fields': {
                        'cycle': cycle_count,
                        'next_wait': 600
                    }}
                )
                time.sleep(10*60)
                
            except Exception as e:
                logger.error("Error in main loop",
                    extra={'extra_fields': {
                        'cycle': cycle_count,
                        'error': str(e),
                        'retry_wait': 3600
                    }},
                    exc_info=True
                )
                time.sleep(60*60)
    
    except Exception as e:
        logger.critical("Critical error in main function",
            extra={'extra_fields': {
                'error': str(e),
                'status': 'shutdown'
            }},
            exc_info=True
        )
        raise

import asyncio

if __name__ == "__main__":
    logger.info("Starting $EXMPLR social media agent",
        extra={'extra_fields': {
            'component': 'worker',
            'status': 'startup',
            'pid': os.getpid()
        }}
    )
    asyncio.run(main())
