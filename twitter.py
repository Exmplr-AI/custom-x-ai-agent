import tweepy
import time
import random
from datetime import datetime, date
import os
from dotenv import load_dotenv
from openai import OpenAI
import logging

from ai_data import Data_generation
from exmplr_API_Tweet_Class import find_enquiry
from collect_news import collect_initial_news, check_latest_feed
from storage_manager import StorageManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Load OpenAI API key from environment
gen_ai = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)
logger.info("OpenAI client initialized")


class Twitter:


    def __init__(self) -> None:
        logger.info("Initializing Twitter agent...")

        # Load Twitter credentials
        logger.info("Loading Twitter API credentials")
        self.api_key = os.getenv('api_key')
        self.api_secret = os.getenv('api_secret')
        self.bearer = os.getenv('bearer')
        self.access = os.getenv('access')
        self.access_secret = os.getenv('access_secret')

        # Initialize Twitter client
        logger.info("Creating Twitter client instance")
        self.client = tweepy.Client(
            bearer_token=self.bearer,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access,
            access_token_secret=self.access_secret,
            wait_on_rate_limit=True
        )
        
        # Get user info
        logger.info("Fetching agent account information")
        me = self.client.get_me()
        self.user_id = me.data.id
        self.username = me.data
        logger.info(f"Authenticated as: {self.username}")

        # Initialize components
        logger.info("Initializing storage manager")
        self.storage = StorageManager()
        
        logger.info("Initializing AI data generation")
        self.gen_ai = Data_generation()
        
        # Initialize tracking lists
        logger.info("Setting up interaction tracking")
        self.initial_mention = []
        self.keywords_tweeted = []

        # Import RSS feeds from config
        logger.info("Loading RSS feed configuration")
        from news_config import RSS_FEEDS, FEED_CATEGORIES
        
        # Use daily news feeds for Twitter updates
        self.links = FEED_CATEGORIES["daily_news"]
        logger.info(f"Monitoring {len(self.links)} news feeds")
        
        # Collect initial news data
        logger.info("Collecting initial news data...")
        self.latest_news = collect_initial_news(self.links)
        logger.info(f"Collected news from {len(self.latest_news)} sources")
        
        logger.info(f"Twitter agent initialization complete: {self.username}")


    
    def collect_initial_mention(self):
        logger.info("Starting collection of initial mentions...")
        mention_count = 0
        
        for response in tweepy.Paginator(self.client.get_users_mentions,
                                     self.user_id,
                                     tweet_fields=["id","created_at", "text", "attachments", "author_id"
                                         , "conversation_id", "entities", "geo", "lang", "in_reply_to_user_id"
                                         , "possibly_sensitive", "public_metrics"
                                         , "referenced_tweets", "reply_settings", "withheld", "source"],
                                     max_results=10 , ).flatten(limit=10):
            self.initial_mention.append(response.id)
            mention_count += 1
            
        logger.info(f"Collected {mention_count} initial mentions")
    

    def make_reply_to_mention(self):

        try:
            for response in tweepy.Paginator(self.client.get_users_mentions,
                                     self.user_id,
                                     tweet_fields=["id","created_at", "text", "attachments", "author_id"
                                         , "conversation_id", "entities", "geo", "lang", "in_reply_to_user_id"
                                         , "possibly_sensitive", "public_metrics"
                                         , "referenced_tweets", "reply_settings", "withheld", "source"],
                                     max_results=5 , ).flatten(limit=5):
                time.sleep(10)
                id = response.id
                if id in self.initial_mention:
                    break
                original_tweet = response.text
                author_id = response.author_id
                if author_id == self.user_id:
                    logger.info("Skipping own tweet")
                    continue
                try:
                    ref_tweet = response.referenced_tweets[0]
                    logger.debug("Processing referenced tweet:")
                    logger.debug(f"Original tweet: {original_tweet}")
                    logger.debug(f"Referenced tweet: {ref_tweet}")
                    ref_response = self.client.get_tweet(ref_tweet.id)
                    ref_tweet = ref_response.data.text

                except Exception as e:
                    logger.warning(f"Error fetching referenced tweet: {str(e)}")
                    ref_tweet = "   "
                total_tweet = ref_tweet + "\n\n" + original_tweet
                logger.debug(f"Combined tweet content: {total_tweet}")
                # total_tweet = total_tweet.replace("@exmplr_agent"," ")
                answer = find_enquiry(total_tweet)
                if answer !='failed':
                    time.sleep(60)
                    self.client.like(id)
                    time.sleep(60)
                    self.client.create_tweet(text=answer,in_reply_to_tweet_id=id)
                    logger.info(f"Successfully replied to tweet: {original_tweet[:100]}...")
                    self.initial_mention.append(id)
                    time.sleep(10*60)
                else:
                    logger.error("Failed to generate response from OpenAI")

        except Exception as e:
            logger.error(f"Error in mention handling: {str(e)}")
            logger.info("Sleeping for 15 minutes before retry")
            time.sleep(15*60)
            
    
    
    def target_keywords(self):
        try:
            keywords = ['BTC','Agsys','Agsys']
            keyword = random.choice(keywords)
            c = 0
            logger.info(f"Searching for tweets with keyword: {keyword}")
            for response in tweepy.Paginator(self.client.search_recent_tweets,
                                     keyword,
                                     tweet_fields=["id","created_at", "text", "attachments", "author_id"
                                         , "conversation_id", "entities", "geo", "lang", "in_reply_to_user_id"
                                         , "possibly_sensitive", "public_metrics"
                                         , "referenced_tweets", "reply_settings", "withheld", "source"],
                                     max_results=10 , ).flatten(limit=10):
                time.sleep(10)
                tweet_id = response.id
                c = c+1
                if tweet_id not in self.keywords_tweeted:
                    try:
                        tweet_text = response.text
                        logger.debug(f"Processing tweet: {tweet_text[:100]}...")
                        
                        ref_tweet_id = response.referenced_tweets[0].id
                        ref_tweet = self.client.get_tweet(ref_tweet_id)
                        logger.debug(f"Found referenced tweet: {ref_tweet.id}")
                        
                        time.sleep(20)
                        ref_tweet_text = ref_tweet.data.text
                        logger.debug(f"Referenced tweet content: {ref_tweet_text[:100]}...")

                    except Exception as e:
                        logger.warning(f"Error fetching referenced tweet: {str(e)}")
                        ref_tweet_text = "   "

                    tweet_text = response.text
                    time.sleep(60)
                    logger.info("Generating reply...")
                    reply_tweet = self.gen_ai.make_a_reply(tweet_text,ref_tweet_text)
                    
                    if reply_tweet != 'failed':
                        logger.info("Posting reply...")
                        self.client.create_tweet(text=reply_tweet,in_reply_to_tweet_id=tweet_id)
                        logger.info(f"Successfully replied to tweet ID: {tweet_id}")
                        self.keywords_tweeted.append(tweet_id)
                        time.sleep(10*60)
                            
                else:
                    logger.info(f"Already interacted with tweet ID: {tweet_id}")
                
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            logger.info("Sleeping for 5 minutes before retry")
            time.sleep(300)
            
    def analyze_news(self, is_weekly=False):
        try:
            post_type = "weekly research" if is_weekly else "news"
            logger.info(f"Starting {post_type} analysis...")
            
            url = random.choice(list(self.latest_news.keys()))
            logger.info(f"Checking feed: {url}")
            
            result = check_latest_feed(url, self.latest_news[url])
            if result:
                logger.info("New content found, updating cache")
                self.latest_news[url] = result
                
                logger.info("Generating tweet content...")
                tweet = self.gen_ai.analyze_the_tweet(result, is_weekly=is_weekly)
                
                if tweet != 'failed':
                    logger.info("Posting tweet...")
                    self.client.create_tweet(text=tweet)
                    logger.info(f"Successfully posted {post_type} tweet from {url}")
                    time.sleep(10*60)
                else:
                    logger.error("Failed to generate tweet content")
            else:
                logger.info(f"No new content found in {url}")
        except Exception as e:
            logger.error(f"Error in news analysis: {str(e)}")
            logger.info("Sleeping for 15 minutes before retry")
            time.sleep(60*15)
        
