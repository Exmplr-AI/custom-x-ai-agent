import time
import asyncio
import os
import random
import re
from datetime import datetime
from dotenv import load_dotenv
import openai
from openai import OpenAI
from research_manager import ResearchManager
from storage_manager import StorageManager
from exmplr_API_Tweet_Class import generate_exmplr_api_payload, generate_exmplr_link, extract_condition


class Data_generation:

    def __init__(self) -> None:
        # Load environment variables
        load_dotenv()
        
        # Load OpenAI API key from environment
        self.gen_ai = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.storage = StorageManager()
        self.research_mgr = ResearchManager(self.storage)
        # Marketing content types focused on platform capabilities
        self.content_types = [
            "Platform Update: Advanced Trial Analytics",
            "Research: Clinical Data Insights",
            "Innovation: AI-Powered Trial Matching",
            "Feature: Real-time Trial Monitoring",
            "Development: Research Data Pipeline",
            "Use Case: Trial Recruitment Optimization",
            "Technical: Machine Learning Analysis",
            "Impact: Clinical Research Acceleration",
            "Research: Patient Matching Efficiency"
        ]
        # Major update types that warrant threads
        self.major_updates = [
            "Platform Update",
            "Technical",
            "Innovation"
        ]
        # Feature highlights with specific platform metrics
        self.feature_highlights = {
            "Trial Analytics": "processes 10,000+ trials daily",
            "Patient Matching": "achieves 95% matching accuracy",
            "Data Pipeline": "analyzes 1M+ data points hourly",
            "Research Tools": "supports 500+ research centers",
            "Trial Monitoring": "tracks 50,000+ trial updates daily",
            "Recruitment": "reduces matching time by 80%",
            "Data Analysis": "provides insights from 100+ countries"
        }
        # Platform URL
        self.base_url = "https://app.exmplr.io"

    def get_platform_url(self, query_type=None, query_text=None, article_url=None):
        """Get platform URL based on query type"""
        if query_type == 'news' and article_url:
            return article_url
        elif query_type == 'clinical_trial' and query_text:
            # Extract condition and age
            condition = extract_condition(query_text)
            age_match = re.search(r"\b(\d{1,3})\s*(years|yrs)?\s*(old)?", query_text, re.IGNORECASE)
            age = int(age_match.group(1)) if age_match else None
            
            # Generate API payload and link
            topics = [condition]
            context = {"age": age, "location": "United States"}
            api_payload = generate_exmplr_api_payload(query_text, topics, context)
            return generate_exmplr_link(api_payload)
        return self.base_url

    def clean_content(self, content, is_weekly=False, query_type=None, query_text=None, article_url=None):
        """Clean and format content with proper thread numbering"""
        platform_url = self.get_platform_url(query_type, query_text, article_url)
        
        # Handle URLs based on content type
        if query_type == 'news' and article_url:
            # For news posts, just return the content without any URL handling
            pass
        else:
            # Fix URLs and references for non-news content
            content = re.sub(r'(https://app\.exmplr\.io)(?:[^\s]*)?(?:\s+\1(?:[^\s]*)?)*', platform_url, content)
            content = re.sub(r'Visit.*?https://app\.exmplr\.io(?:[^\s]*)?', f'Visit {platform_url}', content)
            content = re.sub(r'(?:Learn|Discover) more:.*?https://app\.exmplr\.io(?:[^\s]*)?', f'Visit {platform_url}', content)
            content = re.sub(r'\[(?:link|yourlink|Link to the platform)\]', platform_url, content)
        
        # Fix token and company mentions
        content = re.sub(r'@EXMPLR', '$EXMPLR', content)  # Fix incorrect token symbol
        content = re.sub(r'@exmplr\b', '@exmplrai', content)  # Fix company handle
        
        # Fix percentage and number formatting
        content = re.sub(r'\((\d+)/\d+\)(\d+)%', r'\1\2%', content)  # Fix ((1/3)90% -> 90%
        content = re.sub(r'(\d+)/\d+%', r'\1%', content)  # Fix 1/3% -> 1%
        
        # Process content based on whether it's a thread or single tweet
        if '(1/' in content:  # Thread
            tweets = content.split('\n\n')
            processed_tweets = []
            
            for tweet in tweets:
                # Ensure proper thread numbering format
                if is_weekly:
                    tweet = re.sub(r'^(?:\(?(\d+)/(\d+)\)?)?(.*)$', 
                                 lambda m: f"({m.group(1) or '1'}/7) {m.group(3).strip()}", 
                                 tweet.strip())
                else:
                    tweet = re.sub(r'^(?:\(?(\d+)/(\d+)\)?)?(.*)$', 
                                 lambda m: f"({m.group(1) or '1'}/3) {m.group(3).strip()}", 
                                 tweet.strip())
                
                # Ensure single emoji after numbering
                if '(' in tweet and ')' in tweet:
                    pre_part = tweet[:tweet.find(')')+1].strip()
                    post_part = tweet[tweet.find(')')+1:].strip()
                    emojis = re.findall(r'[\U00010000-\U0010ffff]', post_part)
                    if emojis:
                        post_part = re.sub(r'[\U00010000-\U0010ffff]', '', post_part)
                        tweet = f"{pre_part} {emojis[0]} {post_part.strip()}"
                    else:
                        tweet = f"{pre_part} 📝 {post_part.strip()}"
                
                # Clean up extra punctuation
                tweet = re.sub(r'!+', '!', tweet)  # Multiple exclamation marks
                tweet = re.sub(r'\.+', '.', tweet)  # Multiple periods
                tweet = re.sub(r'\s*[.!?]+\s*([.!?])', r'\1', tweet)  # Multiple ending punctuation
                tweet = re.sub(r'\s+:', ':', tweet)  # Space before colon
                
                # Remove common redundant phrases
                redundant_phrases = [
                    r'Exciting\s+(?:news|update|times)!?\s*',
                    r'Ready\s+to\s+[^.!?]+[.!?]\s*',
                    r'Don\'t\s+miss\s+out[.!]?\s*',
                    r'Stay\s+tuned[^.!?]*[.!?]\s*',
                    r'check\s+(?:it\s+)?out\b',
                    r'click\s+here\b',
                    r'learn\s+more\s+about\b',
                    r'discover\s+more\b',
                    r'explore\s+more\b',
                    r'Let\'s\s+[^.!?]+[.!?]\s*',
                    r'Experience\s+[^.!?]+now[.!?]\s*'
                ]
                for phrase in redundant_phrases:
                    tweet = re.sub(phrase, '', tweet, flags=re.IGNORECASE)
                
                # Clean up extra spaces, newlines, and punctuation
                tweet = re.sub(r'\s+', ' ', tweet)
                tweet = re.sub(r'\s*[.!?]+\s*$', '!', tweet)  # End with single punctuation
                tweet = tweet.strip()
                
                # Remove all hashtags
                tweet = re.sub(r'#\w+', '', tweet)
                
                processed_tweets.append(tweet.strip())
            
            content = '\n\n'.join(processed_tweets)
        else:  # Single tweet
            # Handle emoji for single tweets
            emojis = re.findall(r'[\U00010000-\U0010ffff]', content)
            if emojis:
                # Keep first emoji and remove others
                content = re.sub(r'[\U00010000-\U0010ffff]', '', content)
                content = f"{emojis[0]} {content.strip()}"
            else:
                # Add default emoji if none present
                content = f"🔬 {content.strip()}"
            
            # Remove all hashtags
            content = re.sub(r'#\w+', '', content)
        
        # Fix emoji spacing
        def add_emoji_space(match):
            emoji, text = match.groups()
            if text.startswith(('!', '?', '.', ',', ':', ';')):
                return f"{emoji}{text}"
            return f"{emoji} {text}"
        
        content = re.sub(r'([\U00010000-\U0010ffff])([^\s\U00010000-\U0010ffff])', add_emoji_space, content)
        content = re.sub(r'([^\s\U00010000-\U0010ffff])([\U00010000-\U0010ffff])', r'\1 \2', content)
        
        # Format large numbers with commas, but skip URLs
        def add_commas(match):
            # Skip if part of a URL
            before_match = content[:match.start()]
            if 'http' in before_match and '/' in before_match[before_match.rfind('http'):]:
                return match.group(0)
            num = int(match.group(1))
            return f"{num:,}"
        content = re.sub(r'(\d{4,})', add_commas, content)
        
        return content

    async def analyze_the_tweet(self, data, is_weekly=False):
        """Generate tweet content based on input data"""
        try:
            await asyncio.sleep(1)
            data = str(data)

            if is_weekly:
                # First gather research data
                research_data = await self.research_mgr.generate_research(data)
                research_context = ""
                if research_data and research_data[0]:  # research_data is (text, urls) tuple
                    research_context = f"\n\nLatest Research Insights:\n{research_data[0]}"

                prompt = f'''
                Create a detailed Twitter thread (7 tweets) about this research topic.
                
                Topic: {data}
                {research_context}
                
                Guidelines:
                - Start with key statistics or compelling fact
                - Include specific metrics and data points
                - Reference $EXMPLR Agent token in tweets 1, 4, and 7
                - Include @exmplrai mention in final tweet
                - Use industry-specific insights
                - End with actionable conclusion
                - Format numbers with commas for readability
                - Keep each tweet under 280 characters
                
                Format:
                - Each tweet MUST start with "(X/7)" format (e.g., "(1/7)")
                - Add one relevant emoji after the number
                - Keep each tweet focused and impactful
                - Use {self.base_url} only in final tweet
                - No hashtags or redundant phrases
                - Ensure proper spacing around emojis
                
                Example Format:
                (1/7) 🚀 First tweet content with $EXMPLR Agent token...
                
                (2/7) 📊 Second tweet content...
                
                (3/7) 💡 Third tweet content...
                '''
            else:
                prompt = f'''   
                Create a concise, impactful tweet about this topic.
                
                Topic: {data}
                
                Guidelines:
                - Focus on one key message (be concise)
                - Include specific metrics when relevant
                - Use $EXMPLR Agent token mention
                - Can mention @exmplrai for company updates
                - State ONLY the key findings or insights
                - Format numbers with commas for readability
                - Keep under 280 characters
                - Exactly one emoji at start of tweet
                - No hashtags
                - No links
                - No mentions of @exmplrai or $EXMPLR
                - No "stay tuned" or "more updates"
                - No calls to action of any kind
                - No promotional content
                - ONLY the news facts themselves
                
                Example: "🔬 New cancer treatment achieves 85% success rate in clinical trials, demonstrating significant effectiveness in patient outcomes."
                '''

            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip().replace('"', '')
            content = self.clean_content(content, is_weekly)
            print("Generated content:\n" + content)
            await asyncio.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            await asyncio.sleep(1)
            return 'failed'

    def make_a_reply(self, original_tweet='', reference_tweet=''):
        """Generate reply to user tweets"""
        try:
            time.sleep(1)
            
            # Check if this is a clinical trial query
            is_clinical_trial = any(term in original_tweet.lower() for term in [
                'trial', 'study', 'clinical', 'research', 'patient', 'treatment',
                'drug', 'therapy', 'recruitment', 'eligibility'
            ])
            
            query_type = 'clinical_trial' if is_clinical_trial else None
            platform_url = self.get_platform_url(query_type, original_tweet)

            prompt = f"""
            Generate a single concise reply tweet.
            
            Guidelines:
            - Keep it under 280 characters
            - Include one relevant feature highlight
            - Add one clear call-to-action
            - Include relevant emoji (maximum 1)
            - Format numbers with commas for readability
            - MUST include $EXMPLR token mention
            - Can also use @exmplrai mention
            - No hashtags needed
            
            Context:
            About Me (Agent):
            - I'm $EXMPLR Agent, an AI assistant for clinical research
            - I help users find and understand clinical trials
            - I provide research insights and trial analysis
            - I assist with trial recruitment queries
            - I monitor trial updates and changes

            About ExmplrAI (Company):
            - @exmplrai provides a comprehensive clinical research insights platform
            - The platform offers advanced trial analytics and data analysis
            - Features include:
              * Active trial recruitment tracking
              * Expanded access program details
              * Clinical research data analysis
              * Trial eligibility matching
              * Real-time trial updates
              * Comprehensive analytics dashboard

            Response Style:
            - For "what do you do" - focus on agent capabilities
            - For "what is ExmplrAI" - explain both agent and platform
            - Prioritize professional and helpful tone
            - Always highlight relevant capabilities based on the query
            
            Required Elements:
            - $EXMPLR token mention
            - Platform feature highlight
            - Clear call-to-action
            - Link to platform
            
            Important:
            - Always use {platform_url} for any links
            - Never use placeholder text
            - Keep response focused and impactful
            - Ensure $EXMPLR token is included
            
            Original tweet: {original_tweet}
            """

            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip().replace('"', '')
            content = self.clean_content(content, is_weekly=False, query_type=query_type, query_text=original_tweet)
            print("Generated reply:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'

    async def generate_marketing_post(self):
        """Generate marketing content about $EXMPLR"""
        try:
            await asyncio.sleep(1)
            content_type = random.choice(self.content_types)
            is_major_update = any(update in content_type for update in self.major_updates)
            
            # Select random feature highlight
            feature = random.choice(list(self.feature_highlights.keys()))
            metric = self.feature_highlights[feature]
            
            # Get relevant research insights if possible
            research_context = ""
            try:
                research_insights = await self.research_mgr.extract_relevant_insights(content_type)
                if research_insights:
                    research_context = f"\n\nRecent Research Insights:\n{research_insights}"
            except Exception as e:
                print(f"Warning: Could not get research insights: {str(e)}")
                # Continue without research insights
            
            if is_major_update:
                prompt = f"""
                Generate an informative Twitter thread (3 tweets) about {content_type}.
                
                Content Structure:
                Tweet 1: Platform Achievement
                - Lead with key platform metric: {feature} - {metric}
                - Include $EXMPLR mention naturally
                - Focus on platform capabilities
                - Highlight research impact
                
                Tweet 2: Technical Innovation
                - Showcase platform features
                - Include specific performance metrics
                - Emphasize research advantages
                - Use clinical research terminology
                
                Tweet 3: Research Impact
                - Share real-world research outcomes
                - Include @exmplrai mention
                - Reference $EXMPLR platform
                - Link to {self.base_url}
                {research_context}
                
                Style Requirements:
                - Professional research focus
                - Clinical trial expertise
                - Each tweet under 280 characters
                - One relevant research emoji per tweet
                - Format numbers with commas
                - Use medical/research terminology
                
                Technical Format:
                - Start each tweet with "(X/3)"
                - Add research emoji after numbering
                - No promotional language
                - No investment advice
                - No "buy", "invest", or price references
                - Natural integration of $EXMPLR mentions
                
                Remember:
                - Focus on platform capabilities
                - Share concrete metrics
                - Maintain scientific credibility
                - Keep $EXMPLR mentions organic
                """
            else:
                prompt = f"""
                Generate a single powerful tweet about {content_type}.
                
                Content Requirements:
                - Feature: {feature} - {metric}
                - Include specific platform metrics
                - Focus on research capabilities
                - Highlight clinical trial features
                - Use medical/research terminology
                - Reference platform innovations
                {research_context}
                
                Style Requirements:
                - Professional research tone
                - Include $EXMPLR mention naturally
                - @exmplrai mention if platform update
                - Focus on platform capabilities
                - One research-related emoji
                - Format numbers with commas
                
                Technical Requirements:
                - Keep under 280 characters
                - Use {self.base_url} for link
                - No promotional language
                - No investment advice
                - No "buy", "invest", or price references
                - Natural integration of $EXMPLR
                
                Example Structure:
                [Research Emoji] Platform achievement + Specific metric + $EXMPLR platform capability
                
                Remember:
                - Focus on research impact
                - Share concrete platform metrics
                - Keep scientific credibility
                - Make platform benefits clear
                """
            
            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip().replace('"', '')
            content = self.clean_content(content, is_weekly=False, query_type='marketing')
            print("Generated marketing content:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'
