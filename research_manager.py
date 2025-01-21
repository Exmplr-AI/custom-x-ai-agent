import os
import re
import requests
import feedparser
import openai
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from newspaper import Article, ArticleException
from datetime import datetime, timedelta
from storage_manager import StorageManager
from rate_limit_manager import RateLimitManager
import urllib3

# Disable urllib3 warnings
urllib3.disable_warnings()

class ResearchManager:
    def __init__(self, storage_manager: StorageManager):
        # Initialize storage
        self.storage = storage_manager
        
        # Load OpenAI API key from environment
        self.gen_ai = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # RSS Feeds for AI & DeSci
        self.rss_feeds = [
            "https://pubmed.ncbi.nlm.nih.gov/rss/search/1puh2wJZbabDSaexjIHnmQiSza4yAs7w5fFmnyzJXgjtz87MqY/?limit=15&utm_campaign=pubmed-2&fc=20240319133207",
            "http://export.arxiv.org/rss/cs.AI",
            "https://www.technologyreview.com/feed/",
            "https://ai.googleblog.com/feeds/posts/default?alt=rss",
            "https://rss.sciencedirect.com/publication/science/09333657",
            "https://rss.sciencedirect.com/publication/science/13865056",
            "https://rss.sciencedirect.com/publication/science/26665212",
            "https://blog.google/technology/health/rss/"
        ]
        
        # Initialize API keys
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID")
        
        # Initialize rate limiter
        self.rate_limiter = RateLimitManager(self.storage)

    async def get_recent_research(self):
        """Get recent research for content inspiration"""
        try:
            # Get last 5 research posts from storage
            interactions = await self.storage.get_recent_interactions(5)
            return [interaction['response_text'] for interaction in interactions 
                   if interaction['query_type'] == 'research']
        except Exception as e:
            print(f"Error getting recent research: {e}")
            return []
    
    async def extract_relevant_insights(self, topic):
        """Extract insights relevant to specific topic"""
        try:
            recent_research = await self.get_recent_research()
            if not recent_research:
                return ""
                
            # Combine recent research for analysis
            combined_research = "\n\n".join(recent_research)
            
            prompt = f"""
            Extract key insights from this research that are relevant to: {topic}
            
            Research Content:
            {combined_research}
            
            Format the response as 2-3 key points that could enhance content about {topic}.
            Focus on statistics, trends, and specific findings.
            Keep it concise and impactful.
            """
            
            response = self.gen_ai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            insights = response.choices[0].message.content.strip()
            return insights
            
        except Exception as e:
            print(f"Error extracting insights: {e}")
            return ""

    async def fetch_rss_articles(self, allow_recent=False):
        """
        Fetch articles from RSS feeds
        
        Parameters:
        allow_recent (bool): If True, includes recent articles when no new ones are found
        """
        articles = []
        recent_articles = []  # Store recent articles as backup
        
        # Get posted URLs from storage
        interactions = await self.storage.get_recent_interactions(100)
        posted_urls = [i.get('metadata', {}).get('url') for i in interactions 
                      if i.get('metadata', {}).get('url')]
        posted_urls = [url for url in posted_urls if url]  # Filter None values
        
        for feed_url in self.rss_feeds:
            try:
                # Check rate limits before accessing feed
                if not await self.rate_limiter.can_access(feed_url):
                    print(f"Rate limited, skipping feed: {feed_url}")
                    continue

                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    print(f"No entries found for feed: {feed_url}")
                    await self.rate_limiter.record_failure(feed_url)
                    continue

                await self.rate_limiter.record_success(feed_url)
                
                for entry in feed.entries[:5]:  # Check more entries
                    article = {
                        "title": entry.title,
                        "link": entry.link
                    }
                    
                    if entry.link not in posted_urls:
                        articles.append(article)
                    elif allow_recent:
                        # Store as recent if it's in our history
                        recent_articles.append(article)
                        
            except Exception as e:
                print(f"Error fetching RSS feed {feed_url}: {e}")
                await self.rate_limiter.record_failure(feed_url)
                continue
        
        # If no new articles and allow_recent is True, use recent ones
        if not articles and allow_recent and recent_articles:
            print("No new articles found, using recent articles as fallback")
            # Sort recent articles to get the most relevant ones
            sorted_recent = sorted(
                recent_articles,
                key=lambda x: posted_urls.index(x["link"]) if x["link"] in posted_urls else float('inf'),
                reverse=True  # Most recently used first
            )
            return sorted_recent[:3]  # Return up to 3 recent articles
            
        return articles[:3]  # Limit to 3 new articles

    def search_google(self, query):
        """Search for articles using Google Custom Search with domain filtering"""
        if not (self.google_api_key and self.search_engine_id):
            print("Google Search API credentials not configured")
            return []

        try:
            # Add focus on news and blog sites
            search_query = f"{query} (site:techcrunch.com OR site:venturebeat.com OR site:wired.com OR site:thenextweb.com OR site:medium.com)"
            url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={self.google_api_key}&cx={self.search_engine_id}"
            response = requests.get(url).json()
            articles = response.get('items', [])[:5]
            
            # Filter out already posted URLs
            new_articles = [
                {"title": a["title"], "link": a["link"]} 
                for a in articles
            ]
            
            return new_articles[:3]
        except Exception as e:
            print(f"Error searching Google: {e}")
            return []

    async def extract_article_text(self, url):
        """Extract content from article URL with multiple fallback methods"""
        # Check rate limits before accessing URL
        if not await self.rate_limiter.can_access(url):
            print(f"Rate limited, skipping URL: {url}")
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Method 1: Direct newspaper3k extraction
        try:
            article = Article(url)
            article.download()
            article.parse()
            if article.text and len(article.text.strip()) > 100:  # Ensure meaningful content
                await self.rate_limiter.record_success(url)
                return article.text[:4000]  # Limit input size for GPT-4
        except Exception as e:
            print(f"Primary extraction failed for {url}: {e}")

        # Method 2: Custom request with headers
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                article = Article(url)
                article.set_html(response.text)
                article.parse()
                if article.text and len(article.text.strip()) > 100:
                    await self.rate_limiter.record_success(url)
                    return article.text[:4000]
        except Exception as e:
            print(f"Secondary extraction failed for {url}: {e}")

        # Method 3: Try to extract main content from HTML
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Remove script and style elements
                text = re.sub(r'<script.*?</script>', '', response.text, flags=re.DOTALL)
                text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                # Remove extra whitespace
                text = ' '.join(text.split())
                if text and len(text.strip()) > 100:
                    await self.rate_limiter.record_success(url)
                    return text[:4000]
        except Exception as e:
            print(f"Fallback extraction failed for {url}: {e}")

        await self.rate_limiter.record_failure(url)
        print(f"All extraction methods failed for {url}")
        return None

    async def generate_research(self, topic):
        """Generate research content from multiple sources"""
        try:
            # First try with only new articles
            print(f"Searching for articles about: {topic}")
            google_articles = self.search_google(topic)
            rss_articles = await self.fetch_rss_articles(allow_recent=False)
            
            all_articles = google_articles + rss_articles

            # If no new articles found, try with recent ones
            if not all_articles:
                print(f"No new articles found for {topic}, trying with recent articles")
                rss_articles = await self.fetch_rss_articles(allow_recent=True)
                all_articles = google_articles + rss_articles
                
                if not all_articles:
                    print(f"No articles found for {topic}, even with recent ones")
                    return None, None

            # Extract and combine content
            print("Extracting content from articles...")
            combined_text = ""
            new_urls = []
            successful_extractions = 0

            for article in all_articles:
                print(f"Processing article: {article['title']}")
                text = await self.extract_article_text(article["link"])
                if text:
                    combined_text += f"\n\nArticle: {article['title']}\n{text[:2000]}"
                    new_urls.append(article["link"])
                    successful_extractions += 1
                
                # Ensure we have at least 2 successful extractions
                if successful_extractions < 2 and article == all_articles[-1]:
                    print("Insufficient article extractions, trying with recent articles")
                    more_articles = await self.fetch_rss_articles(allow_recent=True)
                    for more_article in more_articles:
                        if more_article["link"] not in new_urls:
                            text = await self.extract_article_text(more_article["link"])
                            if text:
                                combined_text += f"\n\nArticle: {more_article['title']}\n{text[:2000]}"
                                new_urls.append(more_article["link"])
                                successful_extractions += 1
                                if successful_extractions >= 2:
                                    break

            if not combined_text:
                print("No content could be extracted from articles")
                return None, None

            print("Generating research summary...")
            # Generate research summary using GPT-4
            prompt = f"""
            Create a compelling research thread about '{topic}' based on these articles.

            CRITICAL REQUIREMENTS:
            1. MANDATORY Token Mentions:
               - Tweet 1 MUST include "$EXMPLR"
               - Tweet 4 MUST include "$EXMPLR"
               - Tweet 7 MUST include "$EXMPLR" AND "@exmplrai"
               - NO EXCEPTIONS on token mentions

            2. Format Requirements:
               - Start with "(X/7) [EMOJI]"
               - Be UNDER 240 characters
               - Use exact emoji specified below
               - Be clear and concise
               - Avoid unnecessary words

            Required format for each tweet:
            1. "(1/7) 💡" Hook + $EXMPLR (stat/fact)
            2. "(2/7) 📊" Current trend (data point)
            3. "(3/7) 🔬" Key finding (research)
            4. "(4/7) 💪" Impact + $EXMPLR (result)
            5. "(5/7) 🚀" Future view (prediction)
            6. "(6/7) 🌐" Industry take (perspective)
            7. "(7/7) ✨" CTA + $EXMPLR + @exmplrai

            Key Elements:
            - Use exact numbers and stats
            - Focus on most impactful points
            - Keep sentences short
            - Use active voice
            - Include commas in numbers
            - Add #AIinHealthcare hashtag in tweet 1

            EXAMPLE THREAD (Follow this format exactly):

            (1/7) 💡 AI market hits $136B in 2024! $EXMPLR leads healthcare AI with 68% better outcomes. #AIinHealthcare

            (2/7) 📊 Latest data: 45% of hospitals now use AI for diagnostics, up from 12% in 2023. Efficiency gains average 3.5x.

            (3/7) 🔬 Breakthrough: New AI models show 92% accuracy in early disease detection, matching expert diagnostics.

            (4/7) 💪 Impact: $EXMPLR's AI reduces diagnostic time by 75%, helping doctors treat 3x more patients daily.

            (5/7) 🚀 By 2025, AI will automate 40% of routine medical tasks, freeing doctors for critical care.

            (6/7) 🌐 Industry leaders predict AI-assisted healthcare will become standard in 80% of hospitals by 2026.

            (7/7) ✨ Join the healthcare revolution! $EXMPLR is transforming patient care. Learn more @exmplrai https://app.exmplr.io

            Articles Content:
            {combined_text}
            """

            response = self.gen_ai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            research_text = response.choices[0].message.content.strip()

            # Content validation
            print("Validating content...")
            validation_errors = []
            
            # Check tweet count
            tweets = [t.strip() for t in research_text.split('\n\n') if t.strip()]
            if len(tweets) != 7:
                validation_errors.append(f"Expected 7 tweets, found {len(tweets)}")
            
            # Required emojis for each tweet position
            required_formats = {
                1: "(1/7) 💡",
                2: "(2/7) 📊",
                3: "(3/7) 🔬",
                4: "(4/7) 💪",
                5: "(5/7) 🚀",
                6: "(6/7) 🌐",
                7: "(7/7) ✨"
            }
            
            # Validate each tweet
            for i, tweet in enumerate(tweets, 1):
                # Check exact format with numbering and emoji
                if not tweet.startswith(required_formats[i]):
                    validation_errors.append(f"Tweet {i} must start with '{required_formats[i]}'")
                
                # Check length
                if len(tweet) > 280:
                    validation_errors.append(f"Tweet {i} exceeds 280 characters")
                
                # Check required mentions
                if i in [1, 4, 7] and "$EXMPLR" not in tweet:
                    validation_errors.append(f"Tweet {i} missing $EXMPLR mention")
                
                if i == 7 and "@exmplrai" not in tweet:
                    validation_errors.append("Final tweet missing @exmplrai mention")

            # Handle validation errors
            if validation_errors:
                error_msg = "\n".join(validation_errors)
                print(f"Content validation failed:\n{error_msg}")
                return None, None

            # Store research in database
            await self.storage.store_research(
                topic=topic,
                content=research_text,
                expires_at=(datetime.now() + timedelta(days=7)).isoformat()
            )

            # Store interaction record
            await self.storage.store_interaction({
                'tweet_id': f'research_{int(datetime.now().timestamp())}',
                'query_text': topic,
                'query_type': 'research',
                'response_text': research_text,
                'created_at': datetime.now().isoformat(),
                'metadata': {
                    'urls': new_urls,
                    'successful_extractions': successful_extractions
                }
            })

            print("Successfully generated research content")
            return research_text, new_urls

        except Exception as e:
            error_msg = str(e)
            print(f"Error generating research: {error_msg}")
            
            if "rate_limit" in error_msg.lower():
                print("API rate limit reached. Please try again later.")
            elif "timeout" in error_msg.lower():
                print("Request timed out. Check your internet connection.")
            elif "permission" in error_msg.lower():
                print("API permission error. Check your API key configuration.")
            elif "model" in error_msg.lower():
                print("Model error. Check if GPT-4 is available for your account.")
            else:
                print("An unexpected error occurred. Please try again.")
            
            return None, None