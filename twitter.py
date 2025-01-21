import tweepy
import time
import random
from datetime import datetime, date
import os
from dotenv import load_dotenv
from openai import OpenAI

from ai_data import Data_generation
from exmplr_API_Tweet_Class import find_enquiry
from collect_news import collect_initial_news, check_latest_feed
from storage_manager import StorageManager

# Load environment variables
load_dotenv()

# Load OpenAI API key from environment
gen_ai = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)



class Twitter:


    def __init__(self) -> None:

        ##defining twitter client

        self.api_key = os.getenv('api_key')
        self.api_secret=os.getenv('api_secret')
        self.bearer =os.getenv('bearer')
        self.access = os.getenv('access')
        self.access_secret = os.getenv('access_secret')
        self.client = tweepy.Client(bearer_token=self.bearer,consumer_key=self.api_key,consumer_secret=self.api_secret,access_token=self.access,access_token_secret=self.access_secret, wait_on_rate_limit=True)
        
        me = self.client.get_me()
        self.user_id = me.data.id
        self.username = me.data
        # auth = tweepy.OAuth1UserHandler(self.api_key,self.api_secret,self.access,self.access_secret)

        # self.api1 = tweepy.API(auth)
        # Initialize managers
        self.storage = StorageManager()
        self.gen_ai = Data_generation()
        self.initial_mention = []
        self.keywords_tweeted = []
        self.links = ["https://www.drugs.com/feeds/clinical_trials.xml","https://www.drugs.com/feeds/medical_news.xml","https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml"]
        self.latest_news = collect_initial_news(self.links)
        
        
        
        print("starting the bot : - {}".format(self.username))


    
    def collect_initial_mention(self):

        
        for response in tweepy.Paginator(self.client.get_users_mentions,
                                     self.user_id,
                                     tweet_fields=["id","created_at", "text", "attachments", "author_id"
                                         , "conversation_id", "entities", "geo", "lang", "in_reply_to_user_id"
                                         , "possibly_sensitive", "public_metrics"
                                         , "referenced_tweets", "reply_settings", "withheld", "source"],
                                     max_results=10 , ).flatten(limit=10):
            self.initial_mention.append(response.id)
    

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
                    print("Skipping as its our own tweet\n\n")
                    continue
                try:
                    ref_tweet = response.referenced_tweets[0]
                    print("*********")
                    print(original_tweet)
                    print(ref_tweet)
                    print("*********")
                    ref_response = self.client.get_tweet(ref_tweet.id)
                    ref_tweet = ref_response.data.text

                except Exception as e:
                    print(e)
                    ref_tweet = "   "
                total_tweet = ref_tweet + "\n\n" + original_tweet
                print(total_tweet)
                # total_tweet = total_tweet.replace("@exmplr_agent"," ")
                answer = find_enquiry(total_tweet)
                if answer !='failed':
                    time.sleep(60)
                    self.client.like(id)
                    time.sleep(60)
                    self.client.create_tweet(text=answer,in_reply_to_tweet_id=id)
                    print("Made a reply tweet to {}  \n\n".format(original_tweet))
                    self.initial_mention.append(id)
                    time.sleep(10*60)
                else:
                    print("Skipped due to openai failure\n\n")


        except Exception as e:
            print(e)
            time.sleep(15*60)
            
    
    
    def target_keywords(self):
        try:
            keywords = ['BTC','Agsys','Agsys']
            keyword = random.choice(keywords)
            c = 0
            print("looking for tweets with {} keyword \n".format(keyword))
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
                        print(tweet_text)
                        ref_tweet_id = response.referenced_tweets[0].id
                        ref_tweet = self.client.get_tweet(ref_tweet_id)
                        print(ref_tweet)
                        time.sleep(20)
                        ref_tweet_text = ref_tweet.data.text
                        print("*********")
                        print("ref tweet\n\n")
                        print(ref_tweet_text)
                        print("*********")
    

                    except Exception as e:
                        print(e)
                        ref_tweet_text = "   "

                    tweet_text = response.text
                    time.sleep(60)
                    reply_tweet = self.gen_ai.make_a_reply(tweet_text,ref_tweet_text)
                    if reply_tweet!='failed':
                        self.client.create_tweet(text=reply_tweet,in_reply_to_tweet_id=tweet_id)
                        print("made a reply tweet")
                        self.keywords_tweeted.append(tweet_id)                            
                        time.sleep(10*60)
                            
                else:
                    print("already interacted with this tweet\n\n")
                
        except Exception as e:
            print(e)
            time.sleep(300)
            
    def analyze_news(self, is_weekly=False):
        try:
            url = random.choice(list(self.latest_news.keys()))
            result = check_latest_feed(url,self.latest_news[url])
            if result:
                print("new news found")
                self.latest_news[url] = result
                tweet = self.gen_ai.analyze_the_tweet(result, is_weekly=is_weekly)
                if tweet!='failed':
                    self.client.create_tweet(text=tweet)
                    print(f"Made a {'weekly research' if is_weekly else 'news'} tweet from " + url)
                    time.sleep(10*60)
            else:
                print("Nothing new")
        except Exception as e:
            print(e)
            time.sleep(60*15)
        
