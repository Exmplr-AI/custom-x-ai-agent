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
        # Marketing content types for varied posts
        self.content_types = [
            "Feature Preview: $EXMPLR Agent Blockchain Integration",
            "Roadmap Update: $EXMPLR DeSci Platform",
            "Community: Future of DeSci with $EXMPLR Agent",
            "Vision: $EXMPLR in Clinical Research",
            "Development: Building $EXMPLR Agent Platform",
            "Use Case: $EXMPLR Agent Applications",
            "Innovation: $EXMPLR Features",
            "Technical: $EXMPLR Architecture",
            "Impact: $EXMPLR in Clinical Trials"
        ]
        # Major update types that warrant threads
        self.major_updates = [
            "Roadmap Update",
            "Technical",
            "Feature Preview"
        ]
        # Feature highlights with specific metrics
        self.feature_highlights = {
            "AI Analysis": "reduces analysis time by 60%",
            "Blockchain": "ensures 100% data integrity",
            "ML Pipeline": "processes 1M+ data points daily",
            "Data Extraction": "achieves 99.9% accuracy",
            "Research Acceleration": "cuts trial setup time by 45%"
        }
        # Platform URL
        self.platform_url = "https://app.exmplr.io"

    def clean_content(self, content, is_weekly=False):
        """Clean and format content with proper thread numbering"""
        # Fix URLs and references
        content = re.sub(r'(https://app\.exmplr\.io)(?:.*?\1)+', r'\1', content)  # Remove duplicate URLs
        content = re.sub(r'Visit.*?https://app\.exmplr\.io', 'Visit https://app.exmplr.io', content)
        content = re.sub(r'(?:Learn|Discover) more:.*?https://app\.exmplr\.io', 'Visit https://app.exmplr.io', content)
        content = re.sub(r'\[(?:link|yourlink|Link to the platform)\]', self.platform_url, content)
        content = re.sub(r'\[https://.*?\]', self.platform_url, content)  # Fix broken URL formats
        
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
        
        # Format large numbers with commas
        def add_commas(match):
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
                - Use {self.platform_url} only in final tweet
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
                - Add clear call-to-action
                - Format numbers with commas for readability
                - Keep under 280 characters
                - Exactly one emoji at start of tweet
                - No hashtags needed
                - Avoid redundant phrases
                
                Keep it engaging and professional.
                Always use {self.platform_url} for any links.
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
            - Always use {self.platform_url} for any links
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
            content = self.clean_content(content, is_weekly=False)
            print("Generated reply:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'

    def generate_marketing_post(self):
        """Generate marketing content about $EXMPLR"""
        try:
            time.sleep(1)
            content_type = random.choice(self.content_types)
            is_major_update = any(update in content_type for update in self.major_updates)
            
            # Select random feature highlight
            feature = random.choice(list(self.feature_highlights.keys()))
            metric = self.feature_highlights[feature]
            
            # Get relevant research insights
            research_insights = ""
            try:
                research_insights = asyncio.run(self.research_mgr.extract_relevant_insights(content_type))
            except Exception as e:
                logger.error(f"Error getting research insights: {str(e)}")
                return ""  # Return empty string on error
            research_context = f"\n\nRecent Research Insights:\n{research_insights}" if research_insights else ""
            
            if is_major_update:
                prompt = f"""
                Generate an informative Twitter thread (3 tweets) about {content_type}.
                
                Content Structure:
                Tweet 1: Key Achievement/Announcement
                - Lead with strongest metric/feature: {feature} - {metric}
                - Include $EXMPLR Agent token mention
                - Set up the importance/context
                
                Tweet 2: Technical Details/Benefits
                - Provide specific technical details
                - Include real numbers and metrics
                - Show competitive advantages
                - Use industry terminology
                
                Tweet 3: Impact & Call-to-Action
                - Demonstrate real-world impact
                - Include @exmplrai mention
                - Strong call-to-action
                - Link to {self.platform_url}
                {research_context}
                
                Style Requirements:
                - Professional and authoritative tone
                - Each tweet under 280 characters
                - One relevant emoji per tweet
                - Format numbers with commas
                - Industry-specific insights
                - Focus on tangible benefits
                
                Technical Format:
                - Start each tweet with "(X/3)"
                - Add emoji after numbering
                - No hashtags or redundant phrases
                - No duplicate URLs
                - Proper spacing around emojis
                
                Remember:
                - Be specific and data-driven
                - Focus on real achievements
                - Maintain narrative flow
                - Keep technical accuracy
                """
            else:
                prompt = f"""
                Generate a single powerful tweet about {content_type}.
                
                Content Requirements:
                - Feature: {feature} - {metric}
                - Must include real, specific numbers/stats
                - Focus on tangible benefits and results
                - Highlight competitive advantages
                - Use industry-specific terminology
                - Reference recent developments if relevant
                {research_context}
                
                Style Requirements:
                - Professional and authoritative tone
                - $EXMPLR Agent token mention required
                - @exmplrai mention if company-related
                - One clear, specific call-to-action
                - Exactly one relevant emoji at start
                - Format numbers with commas (e.g., 1,000)
                
                Technical Requirements:
                - Keep under 280 characters
                - Use {self.platform_url} for link
                - No hashtags or redundant phrases
                - No placeholder text or generalities
                - Proper spacing around emojis
                
                Example Structure:
                [Emoji] Specific achievement/metric with $EXMPLR + Real benefit + Clear CTA
                
                Remember:
                - Be specific and data-driven
                - Focus on real results
                - Make every word count
                - Keep it shareable and engaging
                """
            
            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip().replace('"', '')
            content = self.clean_content(content, is_weekly=False)
            print("Generated marketing content:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'
