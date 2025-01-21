import os
import json
import re
import requests
import openai
from openai import OpenAI
import feedparser
from newspaper import Article, ArticleException
from datetime import datetime

class ResearchManager:
    def __init__(self):
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
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # History tracking
        self.history_file = "research_history.json"
        self.history = self.load_history()

    def load_history(self):
        """Load history of posted content"""
        if not os.path.exists(self.history_file):
            return {"posted_urls": [], "posted_research": []}
        with open(self.history_file, "r") as file:
            return json.load(file)

    def save_history(self):
        """Save history of posted content"""
        with open(self.history_file, "w") as file:
            json.dump(self.history, file, indent=4)

    def get_recent_research(self):
        """Get recent research for content inspiration"""
        try:
            history = self.load_history()
            # Get last 5 research posts, newest first
            return history["posted_research"][-5:]
        except Exception as e:
            print(f"Error getting recent research: {e}")
            return []
    
    def extract_relevant_insights(self, topic):
        """Extract insights relevant to specific topic"""
        try:
            recent_research = self.get_recent_research()
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
            
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            insights = response.choices[0].message.content.strip()
            return insights
            
        except Exception as e:
            print(f"Error extracting insights: {e}")
            return ""

    def fetch_rss_articles(self, allow_recent=False):
        """
        Fetch articles from RSS feeds
        
        Parameters:
        allow_recent (bool): If True, includes recent articles when no new ones are found
        """
        articles = []
        recent_articles = []  # Store recent articles as backup
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:  # Check more entries
                    article = {
                        "title": entry.title,
                        "link": entry.link
                    }
                    
                    if entry.link not in self.history["posted_urls"]:
                        articles.append(article)
                    elif allow_recent:
                        # Store as recent if it's in our history
                        recent_articles.append(article)
                        
            except Exception as e:
                print(f"Error fetching RSS feed {feed_url}: {e}")
                continue
        
        # If no new articles and allow_recent is True, use recent ones
        if not articles and allow_recent and recent_articles:
            print("No new articles found, using recent articles as fallback")
            # Sort recent articles to get the most relevant ones
            sorted_recent = sorted(
                recent_articles,
                key=lambda x: self.history["posted_urls"].index(x["link"]),
                reverse=True  # Most recently used first
            )
            return sorted_recent[:3]  # Return up to 3 recent articles
            
        return articles[:3]  # Limit to 3 new articles

    def search_google(self, query):
        """Search for articles using Google Custom Search with domain filtering"""
        if not (self.google_api_key and self.search_engine_id):
            print("Google Search API credentials not configured")
            return []

        # Blocked domains that often restrict access
        blocked_domains = [
            'tandfonline.com',
            'sciencedirect.com',
            'springer.com',
            'wiley.com',
            'academic.oup.com',
            'jstor.org'
        ]

        try:
            # Add focus on news and blog sites
            search_query = f"{query} (site:techcrunch.com OR site:venturebeat.com OR site:wired.com OR site:thenextweb.com OR site:medium.com)"
            url = f"https://www.googleapis.com/customsearch/v1?q={search_query}&key={self.google_api_key}&cx={self.search_engine_id}"
            response = requests.get(url).json()
            articles = response.get('items', [])[:5]
            
            # Filter out blocked domains and already posted URLs
            new_articles = [
                {"title": a["title"], "link": a["link"]} 
                for a in articles 
                if a["link"] not in self.history["posted_urls"] and
                not any(domain in a["link"] for domain in blocked_domains)
            ]
            
            return new_articles[:3]
        except Exception as e:
            print(f"Error searching Google: {e}")
            return []

    def extract_article_text(self, url):
        """Extract content from article URL with multiple fallback methods"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Method 1: Direct newspaper3k extraction
        try:
            article = Article(url)
            article.download()
            article.parse()
            if article.text:
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
                if article.text:
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
                if text:
                    return text[:4000]
        except Exception as e:
            print(f"Fallback extraction failed for {url}: {e}")

        print(f"All extraction methods failed for {url}")
        return None

    def generate_research(self, topic):
        """Generate research content from multiple sources"""
        try:
            # First try with only new articles
            print(f"Searching for articles about: {topic}")
            google_articles = self.search_google(topic)
            rss_articles = self.fetch_rss_articles(allow_recent=False)
            
            all_articles = google_articles + rss_articles

            # If no new articles found, try with recent ones
            if not all_articles:
                print(f"No new articles found for {topic}, trying with recent articles")
                rss_articles = self.fetch_rss_articles(allow_recent=True)
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
                text = self.extract_article_text(article["link"])
                if text:
                    combined_text += f"\n\nArticle: {article['title']}\n{text[:2000]}"
                    new_urls.append(article["link"])
                    successful_extractions += 1
                
                # Ensure we have at least 2 successful extractions
                if successful_extractions < 2 and article == all_articles[-1]:
                    print("Insufficient article extractions, trying with recent articles")
                    more_articles = self.fetch_rss_articles(allow_recent=True)
                    for more_article in more_articles:
                        if more_article["link"] not in new_urls:
                            text = self.extract_article_text(more_article["link"])
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

            Content Guidelines:
            1. Key Elements to Include:
               - Latest statistics and market data
               - Industry trends and developments
               - Technology breakthroughs
               - Future implications
               - Real-world impact
               - Specific metrics (use exact numbers)

            2. Branding Requirements:
               - Mention $EXMPLR Agent token in tweets 1, 4, and 7
               - Include @exmplrai mention in final tweet
               - Use platform URL (https://app.exmplr.io) only in final tweet
               - Maintain professional, authoritative tone

            3. Format Requirements:
               - Exactly 7 tweets
               - Each tweet must start with "(X/7)" format
               - One relevant emoji after the number
               - Keep each tweet under 280 characters
               - Use commas in large numbers (e.g., "1,500" not "1500")
               - Ensure proper spacing around emojis

            4. Content Structure:
               Tweet 1: Hook with compelling statistic + $EXMPLR
               Tweet 2: Current state/trend
               Tweet 3: Key development/breakthrough
               Tweet 4: Impact + $EXMPLR
               Tweet 5: Future implications
               Tweet 6: Industry perspective
               Tweet 7: Call-to-action + $EXMPLR + @exmplrai

            5. Style Guide:
               - Start each tweet with fresh perspective
               - Avoid redundant phrases
               - Use active voice
               - Be specific and data-driven
               - Maintain consistent tone

            Articles Content:
            {combined_text}
            """

            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
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
            
            # Validate each tweet
            for i, tweet in enumerate(tweets, 1):
                # Check numbering format
                if not tweet.startswith(f"({i}/7)"):
                    validation_errors.append(f"Tweet {i} has incorrect numbering format")
                
                # Check length
                if len(tweet) > 280:
                    validation_errors.append(f"Tweet {i} exceeds 280 characters")
                
                # Check required mentions
                if i in [1, 4, 7] and "$EXMPLR" not in tweet:
                    validation_errors.append(f"Tweet {i} missing $EXMPLR mention")
                
                if i == 7 and "@exmplrai" not in tweet:
                    validation_errors.append("Final tweet missing @exmplrai mention")
                
                # Check emoji presence
                if not re.search(r'[\U00010000-\U0010ffff]', tweet):
                    validation_errors.append(f"Tweet {i} missing emoji")

            # Handle validation errors
            if validation_errors:
                error_msg = "\n".join(validation_errors)
                print(f"Content validation failed:\n{error_msg}")
                return None, None

            # Check for duplicates
            if research_text in self.history["posted_research"]:
                print("Avoiding duplicate research post")
                return None, None

            # Update history
            print("Saving to history...")
            self.history["posted_research"].append(research_text)
            self.history["posted_urls"].extend(new_urls)
            self.save_history()

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