import tweepy
import time
import random
import re
import asyncio
from datetime import datetime, date, timezone
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
        
        # Initialize tracking lists and timestamps
        logger.info("Setting up interaction tracking")
        self.initial_mention = []
        self.keywords_tweeted = []
        self._last_timeline_check = 0  # Initialize timeline check tracking

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
                answer = find_enquiry(total_tweet)
                if answer != 'failed':
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

    async def like_tweet(self, tweet_id: str) -> bool:
        """Like a tweet and record the interaction"""
        try:
            self.client.like(tweet_id)
            await self.storage.record_interaction(tweet_id, 'like')
            logger.info(f"Successfully liked tweet {tweet_id}")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to like tweet {tweet_id}: {error_msg}")
            await self.storage.record_failed_interaction(tweet_id, 'like', error_msg)
            return False

    async def retweet(self, tweet_id: str) -> bool:
        """Retweet a tweet and record the interaction"""
        try:
            self.client.retweet(tweet_id)
            await self.storage.record_interaction(tweet_id, 'retweet')
            logger.info(f"Successfully retweeted tweet {tweet_id}")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to retweet {tweet_id}: {error_msg}")
            await self.storage.record_failed_interaction(tweet_id, 'retweet', error_msg)
            return False

    async def quote_tweet(self, tweet_id: str, quote_text: str) -> bool:
        """Quote a tweet and record the interaction"""
        try:
            # Clean up the quote text
            quote_text = re.sub(r'@\w+', '', quote_text)  # Remove mentions
            quote_text = quote_text.strip()
            quote_text = f"{quote_text} #AIinHealthcare"  # Add our hashtag
            
            self.client.create_tweet(quote_tweet_id=tweet_id, text=quote_text)
            await self.storage.record_interaction(tweet_id, 'quote', quote_text)
            logger.info(f"Successfully quoted tweet {tweet_id}")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to quote tweet {tweet_id}: {error_msg}")
            await self.storage.record_failed_interaction(tweet_id, 'quote', error_msg)
            return False

    def evaluate_tier(self, follower_count, metrics, relevance_score, tweet_age, is_verified):
        """Evaluate which interaction tier a tweet qualifies for"""
        try:
            # Validate inputs
            if not isinstance(follower_count, int) or follower_count < 0:
                logger.error("Invalid follower count")
                return 0
                
            if not isinstance(metrics, dict) or not all(key in metrics for key in ['retweet_count', 'like_count']):
                logger.error("Invalid metrics format")
                return 0
                
            if not isinstance(relevance_score, int) or relevance_score < 0:
                logger.error("Invalid relevance score")
                return 0
                
            if not isinstance(tweet_age, (int, float)) or tweet_age < 0:
                logger.error("Invalid tweet age")
                return 0

            # Log tweet evaluation header
            logger.info("\n=== Tweet Quality Evaluation ===")
            
            # Log metrics
            logger.info("\nMetrics Summary:")
            logger.info(f"• Followers: {follower_count:,}")
            logger.info(f"• Verified: {'✓' if is_verified else '✗'}")
            logger.info(f"• Retweets: {metrics['retweet_count']}")
            logger.info(f"• Likes: {metrics['like_count']}")
            logger.info(f"• Relevance: {relevance_score}/6 keywords")
            logger.info(f"• Age: {tweet_age:.1f} hours")

            # Tier 3: All interactions (20K+ followers or verified, high engagement)
            if ((follower_count >= 20000 or is_verified) and
                (metrics['retweet_count'] >= 30 or metrics['like_count'] >= 50) and
                relevance_score >= 3 and tweet_age <= 3):
                return 3
                
            # Tier 2: Like and retweet (10K+ followers, good engagement)
            if (follower_count >= 10000 and
                (metrics['retweet_count'] >= 10 or metrics['like_count'] >= 20) and
                relevance_score >= 2 and tweet_age <= 6):
                return 2
                
            # Tier 1: Like only (verified OR 5K+ followers, basic engagement)
            if ((is_verified or follower_count >= 5000) and
                (metrics['retweet_count'] >= 3 or metrics['like_count'] >= 5) and
                relevance_score >= 1):
                return 1
            
            return 0
            
        except Exception as e:
            logger.error(f"Error in tier evaluation: {str(e)}")
            return 0

    def log_interaction_decision(self, tier_level, follower_count, metrics, relevance_score, tweet_age, is_verified):
        """Log the decision made for tweet interaction tier"""
        if tier_level == 3:
            logger.info("\n✨ TIER 3 QUALIFICATION - Full Interaction Suite")
            logger.info(f"✓ High Influence: {follower_count:,} followers" + (" or Verified" if is_verified else ""))
            logger.info(f"✓ Strong Engagement: {metrics['retweet_count']} RTs, {metrics['like_count']} likes")
            logger.info(f"✓ High Relevance: {relevance_score}/6 keywords")
            logger.info(f"✓ Recent: {tweet_age:.1f} hours old")
            logger.info("Actions: Like + Retweet + Quote")
        elif tier_level == 2:
            logger.info("\n⭐ TIER 2 QUALIFICATION - Like + Retweet")
            logger.info(f"✓ Good Influence: {follower_count:,} followers")
            logger.info(f"✓ Good Engagement: {metrics['retweet_count']} RTs, {metrics['like_count']} likes")
            logger.info(f"✓ Relevant: {relevance_score}/6 keywords")
            logger.info(f"✓ Recent: {tweet_age:.1f} hours old")
            logger.info("Actions: Like + Retweet")
        elif tier_level == 1:
            logger.info("\n⭐ TIER 1 QUALIFICATION - Like Only")
            if is_verified:
                logger.info("✓ Verified Account")
            else:
                logger.info(f"✓ Basic Influence: {follower_count:,} followers")
            logger.info(f"✓ Basic Engagement: {metrics['retweet_count']} RTs, {metrics['like_count']} likes")
            logger.info(f"✓ Basic Relevance: {relevance_score}/6 keywords")
            logger.info("Actions: Like")
        else:
            logger.info("\n❌ No Tier Qualification")
            if not is_verified and follower_count < 5000:
                logger.info("✗ Insufficient influence (needs verified status or 5K+ followers)")
            if metrics['retweet_count'] < 3 and metrics['like_count'] < 5:
                logger.info("✗ Low engagement (needs 3+ RTs or 5+ likes)")
            if relevance_score < 1:
                logger.info("✗ Not relevant (no keywords matched)")

    async def monitor_following_feed(self, max_tweets=100, max_interactions=10):
        """Monitor and interact with tweets from followed accounts.
        
        Args:
            max_tweets (int): Maximum number of tweets to fetch from timeline (default: 100)
            max_interactions (int): Maximum number of interactions to perform (default: 10)
            
        Returns:
            int: Number of successful interactions performed
        """
        # Check if we've monitored recently (using class variable)
        current_time = time.time()
        if hasattr(self, '_last_timeline_check'):
            time_since_last = current_time - self._last_timeline_check
            if time_since_last < 3600:  # Don't check more than once per hour
                logger.info(f"Skipping timeline check - last check was {time_since_last:.1f} seconds ago")
                return 0
        
        # Update last check time
        self._last_timeline_check = current_time
        
        try:
            logger.info("Monitoring timeline for relevant tweets...")
            total_interactions = 0
            
            # Get tweets from followed accounts
            response = self.client.get_home_timeline(
                max_results=max_tweets,
                tweet_fields=["author_id", "created_at", "public_metrics"],
                user_fields=["public_metrics", "verified"],
                expansions=["author_id"]
            )
            
            if not response.data:
                logger.info("No tweets found in timeline")
                return 0
                
            # Create user lookup dictionary
            users = {user.id: user for user in response.includes['users']} if 'users' in response.includes else {}
            
            # Get recent interactions to avoid duplicates
            recent_interactions = await self.storage.get_recent_interactions(limit=1000)
            
            # Process tweets
            for tweet in response.data:
                if total_interactions >= max_interactions:
                    logger.info(f"Reached maximum interactions ({max_interactions})")
                    break
                    
                logger.info(f"\nProcessing tweet: {tweet.id}")
                logger.info(f"Content: {tweet.text[:100]}...")
                
                # Check if we've already interacted with this tweet
                tweet_interactions = [i for i in recent_interactions if i['tweet_id'] == str(tweet.id)]
                if tweet_interactions:
                    logger.info("Already interacted with this tweet:")
                    for interaction in tweet_interactions:
                        logger.info(f"- {interaction['interaction_type']} on {interaction['created_at']}")
                    continue
                
                # Get author info
                author = users.get(tweet.author_id)
                if not author:
                    logger.info("Author info not available")
                    continue
                    
                follower_count = author.public_metrics['followers_count']
                is_verified = getattr(author, 'verified', False)
                
                # Calculate metrics for tier evaluation
                relevance_keywords = ["healthcare", "clinical", "research", "medical", "AI", "trials"]
                relevance_score = sum(1 for k in relevance_keywords if k.lower() in tweet.text.lower())
                metrics = tweet.public_metrics
                tweet_age = (datetime.now(timezone.utc) - tweet.created_at).total_seconds() / 3600
                
                # Evaluate tweet's tier
                tier = self.evaluate_tier(follower_count, metrics, relevance_score, tweet_age, is_verified)
                self.log_interaction_decision(tier, follower_count, metrics, relevance_score, tweet_age, is_verified)
                
                if tier == 0:
                    continue
                
                # Execute interactions based on tier level
                if tier >= 1:
                    logger.info("Attempting Like...")
                    like_result = await self.like_tweet(tweet.id)
                    if like_result:
                        total_interactions += 1
                        await asyncio.sleep(60)
                
                if tier >= 2:
                    logger.info("Attempting Retweet...")
                    retweet_result = await self.retweet(tweet.id)
                    if retweet_result:
                        total_interactions += 1
                        await asyncio.sleep(60)
                
                if tier >= 3:
                    logger.info("Attempting Quote...")
                    article = {
                        'title': tweet.text[:100],
                        'summary': tweet.text,
                        'url': f"https://twitter.com/i/web/status/{tweet.id}"
                    }
                    quote_text = await self.gen_ai.analyze_the_tweet(article)
                    if quote_text != 'failed':
                        quote_result = await self.quote_tweet(tweet.id, quote_text)
                        if quote_result:
                            total_interactions += 1
            
            logger.info(f"Timeline monitoring complete. Total interactions: {total_interactions}")
            return total_interactions
            
        except Exception as e:
            logger.error(f"Error monitoring timeline: {str(e)}")
            return 0

    async def search_and_interact(self, max_interactions_per_search=3, max_interactions_per_hour=15):
        """Search for relevant tweets and interact with them based on quality tiers"""
        try:
            # Keywords to search for
            keywords = [
                "AI healthcare research",
                "clinical trials AI",
                "medical data analysis",
                "#AIinHealthcare"
            ]
            
            total_interactions = 0
            
            for keyword in keywords:
                if total_interactions >= max_interactions_per_hour:
                    logger.info(f"Reached maximum interactions per hour ({max_interactions_per_hour})")
                    break
                    
                logger.info(f"Searching for: {keyword}")
                interactions_this_search = 0
                
                # Search recent tweets
                response = self.client.search_recent_tweets(
                    query=f"{keyword} -is:retweet lang:en has:mentions",
                    tweet_fields=["author_id", "created_at", "public_metrics"],
                    user_fields=["public_metrics", "verified"],
                    expansions=["author_id"],
                    max_results=100
                )
                
                if not response.data:
                    logger.info(f"No tweets found for keyword: {keyword}")
                    continue
                
                # Create user lookup dictionary
                users = {user.id: user for user in response.includes['users']} if 'users' in response.includes else {}
                
                # Get recent interactions to avoid duplicates
                recent_interactions = await self.storage.get_recent_interactions(limit=1000)
                
                # Process tweets
                for tweet in response.data:
                    if interactions_this_search >= max_interactions_per_search:
                        logger.info(f"Reached maximum interactions for this search ({max_interactions_per_search})")
                        break

                    logger.info(f"\nProcessing tweet: {tweet.id}")
                    logger.info(f"Content: {tweet.text[:100]}...")
                    
                    # Check if we've already interacted with this tweet
                    tweet_interactions = [i for i in recent_interactions if i['tweet_id'] == str(tweet.id)]
                    if tweet_interactions:
                        logger.info("Already interacted with this tweet:")
                        for interaction in tweet_interactions:
                            logger.info(f"- {interaction['interaction_type']} on {interaction['created_at']}")
                        continue
                    
                    # Get author info
                    author = users.get(tweet.author_id)
                    if not author:
                        logger.info("Author info not available")
                        continue
                        
                    follower_count = author.public_metrics['followers_count']
                    is_verified = getattr(author, 'verified', False)
                    
                    # Calculate metrics for tier evaluation
                    relevance_keywords = ["healthcare", "clinical", "research", "medical", "AI", "trials"]
                    relevance_score = sum(1 for k in relevance_keywords if k.lower() in tweet.text.lower())
                    metrics = tweet.public_metrics
                    tweet_age = (datetime.now(timezone.utc) - tweet.created_at).total_seconds() / 3600
                    
                    # Evaluate tweet's tier
                    tier = self.evaluate_tier(follower_count, metrics, relevance_score, tweet_age, is_verified)
                    self.log_interaction_decision(tier, follower_count, metrics, relevance_score, tweet_age, is_verified)
                    
                    if tier == 0:
                        continue
                    
                    # Execute interactions based on tier level
                    if tier >= 1:
                        logger.info("Attempting Like...")
                        like_result = await self.like_tweet(tweet.id)
                        if like_result:
                            interactions_this_search += 1
                            total_interactions += 1
                            await asyncio.sleep(60)
                    
                    if tier >= 2 and interactions_this_search < max_interactions_per_search:
                        logger.info("Attempting Retweet...")
                        retweet_result = await self.retweet(tweet.id)
                        if retweet_result:
                            interactions_this_search += 1
                            total_interactions += 1
                            await asyncio.sleep(60)
                    
                    if tier >= 3 and interactions_this_search < max_interactions_per_search:
                        logger.info("Attempting Quote...")
                        article = {
                            'title': tweet.text[:100],
                            'summary': tweet.text,
                            'url': f"https://twitter.com/i/web/status/{tweet.id}"
                        }
                        quote_text = await self.gen_ai.analyze_the_tweet(article)
                        if quote_text != 'failed':
                            quote_result = await self.quote_tweet(tweet.id, quote_text)
                            if quote_result:
                                interactions_this_search += 1
                                total_interactions += 1
                
                # Wait between keyword searches
                await asyncio.sleep(10)
            
            return total_interactions
            
        except Exception as e:
            logger.error(f"Error in search and interactions: {str(e)}")
            return 0

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
            
    def is_content_relevant(self, title, summary):
        """Check if content is directly relevant to EXMPLR's core features"""
        try:
            prompt = f"""
            Determine if this article is directly relevant to EXMPLR's core features:
            - AI in clinical trials
            - Healthcare automation
            - Clinical research optimization
            - Drug discovery
            - Medical data analysis
            - DeSci (Decentralized Science)

            Title: {title}
            Summary: {summary}

            Return ONLY 'relevant' or 'not relevant' based on direct connection to these topics.
            """

            response = gen_ai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            is_relevant = response.choices[0].message.content.strip().lower() == 'relevant'
            if not is_relevant:
                logger.info(f"Article not directly relevant to EXMPLR features: {title}")
            return is_relevant
            
        except Exception as e:
            logger.error(f"Error checking content relevance: {str(e)}")
            return False

    async def analyze_news(self, is_weekly=False):
        try:
            post_type = "weekly research" if is_weekly else "news"
            logger.info(f"Starting {post_type} analysis...")
            
            # Check all feeds for new content
            for url in list(self.latest_news.keys()):
                logger.info(f"Checking feed: {url}")
                
                results = check_latest_feed(url, self.latest_news[url])
                if results:
                    logger.info(f"Found {len(results)} new articles")
                    
                    # Process each new article
                    for article in results:
                        # Skip relevance check for weekly posts
                        if not is_weekly:
                            # Validation Process
                            logger.info(f"\nValidating article: {article['title']}")
                            logger.info("Step 1: Relevance Check")
                            
                            if not self.is_content_relevant(article['title'], article['summary']):
                                logger.info("❌ Failed relevance check - Article not related to EXMPLR features")
                                continue
                            
                            logger.info("✅ Passed relevance check - Article relates to EXMPLR features")
                        else:
                            logger.info(f"\nProcessing weekly research article: {article['title']}")
                        
                        # Step 2: Tweet Generation
                        logger.info("Step 2: Tweet Generation")
                        tweet = await self.gen_ai.analyze_the_tweet(article, is_weekly=is_weekly)
                        
                        if tweet == 'failed':
                            logger.info("❌ Failed tweet generation - Could not create engaging content")
                            continue
                        
                        logger.info("✅ Passed tweet generation - Created engaging content")
                        logger.info(f"Generated Tweet:\n{tweet}")
                        
                        # Step 3: Queue Article
                        logger.info("Step 3: Queue Article")
                        queued = await self.storage.queue_article(
                            title=article['title'],
                            url=article['url'],
                            tweet_content=tweet,
                            source_feed=url,
                            is_weekly=is_weekly
                        )
                        
                        if queued:
                            logger.info("✅ Successfully queued article")
                            logger.info(f"Queue Status: Article '{article['title']}' ready for posting")
                        else:
                            logger.error("❌ Failed to queue article - Database error")
                    
                    # Update cache with new articles if we got results
                    if results:
                        self.latest_news[url] = results
                else:
                    logger.info(f"No new content found in {url}")
            
            # Check Queue for Articles Ready to Post
            logger.info("\nChecking posting queue...")
            next_article = await self.storage.get_next_article()
            
            if next_article:
                logger.info(f"Found article ready for posting: {next_article['title']}")
                logger.info("Attempting to post...")
                
                try:
                    self.client.create_tweet(text=next_article['tweet_content'])
                    await self.storage.mark_article_posted(next_article['id'])
                    logger.info("✅ Successfully posted to Twitter")
                    logger.info(f"Posted Content:\n{next_article['tweet_content']}")
                    return True
                except Exception as e:
                    error_msg = str(e)
                    logger.error("❌ Failed to post article")
                    logger.error(f"Error: {error_msg}")
                    await self.storage.mark_article_failed(next_article['id'], error_msg)
                    return False
            else:
                logger.info("No articles currently ready for posting")
                return False
            
        except Exception as e:
