import time
from openai import OpenAI
import os
import random
import re
from datetime import datetime


class Data_generation:

    def __init__(self) -> None:
        from dotenv import load_dotenv
        load_dotenv()
        self.api_key=os.getenv('OPENAI_API_KEY')
        self.gen_ai = OpenAI(
            api_key=self.api_key
        )
        # Marketing content types for varied posts
        self.content_types = [
            "Feature Preview: $EXMPLR Blockchain Integration",
            "Roadmap Update: $EXMPLR DeSci Platform",
            "Community: Future of DeSci with $EXMPLR",
            "Vision: $EXMPLR in Clinical Research",
            "Development: Building $EXMPLR Platform",
            "Use Case: $EXMPLR Applications",
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

    def clean_content(self, content):
        """Clean and format content"""
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
                # Fix thread numbering
                tweet = re.sub(r'\(?(\d+)/\d+\)?|\(\(\d+/\d+\)\d*\)', 
                             lambda m: f"({m.group(1)}/{'7' if '7)' in content else '3'})", 
                             tweet)
                
                # Stricter token reference handling
                tweet = re.sub(r'\$EXMPLR(?!\s+Agent\s+token)(?:\s+Agent)?(?:\s+tokens?)?', '$EXMPLR Agent token', tweet)
                tweet = re.sub(r'\$EXMPLR\s+Agent\s+tokens', '$EXMPLR Agent token', tweet)
                
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
                
                # Ensure single emoji at start and remove others
                emojis = re.findall(r'[\U00010000-\U0010ffff]', tweet)
                tweet = re.sub(r'[\U00010000-\U0010ffff]', '', tweet)
                if emojis:
                    tweet = f"{emojis[0]} {tweet.strip()}"
                
                # Remove template text and formatting
                tweet = re.sub(r'(?:Sure!.*?specifications:[\s-]*|---.*)', '', tweet)
                
                # Clean up thread numbering
                tweet = re.sub(r'\((\d+)/(\d+)\)\.?', r'(\1/\2)', tweet)  # Standardize format
                tweet = re.sub(r'(\d+)/(\d+)(?!\))', r'(\1/\2)', tweet)   # Add missing parentheses
                
                # Remove more redundant phrases
                redundant_phrases.extend([
                    r'Just imagine[^.!?]*[.!?]\s*',
                    r'Don\'t miss[^.!?]*[.!?]\s*',
                    r'like never before[.!?]\s*',
                    r'transforming tomorrow[^.!?]*[.!?]\s*'
                ])
                
                # Clean up extra spaces, newlines, and punctuation
                tweet = re.sub(r'\s+', ' ', tweet)
                tweet = re.sub(r'\s*[.!?]+\s*$', '!', tweet)  # End with single punctuation
                tweet = tweet.strip()
                
                # Remove all hashtags
                tweet = re.sub(r'#\w+', '', tweet)
                
                processed_tweets.append(tweet.strip())
            
            content = '\n\n'.join(processed_tweets)
        else:  # Single tweet
            # Limit to one emoji
            emojis = re.findall(r'[\U00010000-\U0010ffff]', content)
            if len(emojis) > 1:
                for emoji in emojis[1:]:
                    content = content.replace(emoji, '')
            
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

    def analyze_the_tweet(self, data, is_weekly=False):
        """Generate tweet content based on input data"""
        try:
            time.sleep(1)
            data = str(data)

            if is_weekly:
                prompt = f'''   
                Create a detailed Twitter thread (7 tweets) about this research topic.
                
                Topic: {data}
                
                Guidelines:
                - Start with key statistics or compelling fact
                - Include specific metrics and data points
                - Reference $EXMPLR Agent token in tweets 1, 4, and 7
                - Can mention @exmplrai once in thread
                - Use industry-specific insights
                - End with actionable conclusion
                - Format numbers with commas for readability
                - Keep each tweet under 180 characters
                - Start each tweet with exactly one emoji
                - Focus on clarity and impact
                - Avoid redundant phrases like "check out" or "learn more"
                - No hashtags needed
                - Remove any extra newlines or spaces
                
                Format:
                - Start with single 🧵 emoji
                - Number tweets exactly as (1/7), (2/7), etc.
                - Include relevant emojis (with proper spacing)
                - Keep each tweet focused and impactful
                - Use {self.platform_url} only in final tweet
                - No duplicate URLs or redundant calls-to-action
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
                - Keep under 180 characters
                - Exactly one emoji at start of tweet
                - No hashtags needed
                - Avoid redundant phrases
                
                Keep it engaging and professional.
                Always use {self.platform_url} for any links.
                '''

            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
            )
            
            content = response.choices[0].message.content.replace('"', '')
            content = self.clean_content(content)
            print("Generated content:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'

    def make_a_reply(self, original_tweet='', reference_tweet=''):
        """Generate reply to user tweets"""
        try:
            time.sleep(1)

            prompt = f"""
            Generate a single concise reply tweet.
            
            Guidelines:
            - Keep it under 180 characters
            - Include one relevant feature highlight
            - Add one clear call-to-action
            - Include relevant emoji (maximum 1)
            - Format numbers with commas for readability
            - Can use $EXMPLR token or @exmplrai mention
            - No hashtags needed
            
            Context:
            - AI-driven clinical trial platform
            - Focus on data analysis and research
            - Prioritize professional tone
            
            Important:
            - Always use {self.platform_url} for any links
            - Never use placeholder text
            - Keep response focused and impactful
            
            Original tweet: {original_tweet}
            """

            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
            )
            
            content = response.choices[0].message.content.replace('"', '')
            content = self.clean_content(content)
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
            
            if is_major_update:
                prompt = f"""
                Generate a short Twitter thread (3 tweets) about {content_type}.
                
                Key Points:
                - Highlight: {feature} - {metric}
                - Include $EXMPLR Agent token mention
                - Can mention @exmplrai once in thread
                - One clear call-to-action in final tweet only
                - Format numbers with commas for readability
                - Keep each tweet under 180 characters
                - Exactly one emoji at start of each tweet
                - No hashtags needed
                - Remove redundant phrases
                - Focus on clarity and impact
                
                Format:
                - Number tweets exactly as (1/3), (2/3), (3/3)
                - Tweet 1: Announcement + Feature highlight
                - Tweet 2: Benefits + Metrics
                - Tweet 3: Call-to-action + {self.platform_url}
                
                Important:
                - Use {self.platform_url} only in final tweet
                - No duplicate URLs or redundant phrases
                - Ensure proper emoji spacing
                - Keep content focused and impactful
                """
            else:
                prompt = f"""
                Generate a single powerful tweet about {content_type}.
                
                Include:
                - Feature: {feature} - {metric}
                - $EXMPLR Agent token mention
                - Can mention @exmplrai if relevant
                - One clear call-to-action
                - Exactly one emoji at start
                - Format numbers with commas for readability
                - No hashtags needed
                - Be concise and impactful
                
                Important:
                - Keep under 180 characters
                - Use {self.platform_url} for link
                - No placeholder text
                - Make it shareable and engaging
                """
            
            response = self.gen_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
            )
            
            content = response.choices[0].message.content.replace('"', '')
            content = self.clean_content(content)
            print("Generated marketing content:\n" + content)
            time.sleep(1)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(1)
            return 'failed'
