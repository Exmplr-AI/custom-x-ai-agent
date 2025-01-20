import time
from openai import OpenAI
import os
import random
from datetime import datetime


class Data_generation:

    def __init__(self) -> None:
        from dotenv import load_dotenv
        load_dotenv()
        self.api_key=os.getenv('OPENAI_API_KEY')
        self.gen_ai = OpenAI(
            api_key=self.api_key
        )
        self.content_types = [
            "Feature Preview: Upcoming $EXMPLR Blockchain Integration",
            "Roadmap Update: $EXMPLR DeSci Platform Development",
            "Community Discussion: Future of DeSci with $EXMPLR",
            "Vision Story: $EXMPLR's Role in Clinical Research",
            "Development Update: Building the $EXMPLR Platform",
            "Use Case Preview: Future $EXMPLR Applications",
            "Innovation Spotlight: $EXMPLR's Planned Features",
            "Technical Preview: $EXMPLR Blockchain Architecture",
            "Global Impact: $EXMPLR in Clinical Trials"
        ]


    def analyze_the_tweet(self, data, is_weekly=False):
        try:
            time.sleep(10)
            data = str(data)

            if is_weekly:
                prompt = '''   
                Analyze the data given and create a detailed Twitter thread (5-7 tweets) about this topic.
                Focus on research insights, industry trends, and future implications.
                Include relevant statistics and data points.
                
                {}
                
                Make sure to format as a thread with 🧵 emoji at start and number each tweet.
                Include $EXMPLR token mention where relevant.
                Don't add any unwanted mentions or hashtags.
                '''.format(data)
            else:
                prompt = '''   
                Analyze the data given and make a tweet including the url in a structured way
                
                {}
                
                Make sure to only return the tweet. nothing else must be added to the returned value.
                Also dont add any unwanted mentions in the reply tweet.
                Also Dont add any hashtags in the tweet
                '''.format(data)

            response = self.gen_ai.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-4o",)
            
            contents = response.choices[0].message.content
            content = contents.replace('"',"")
        
            print("Openai Generated tweet - \n" + content)
            time.sleep(50)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(60)
            return 'failed'


    def make_a_reply(self, original_tweet='', reference_tweet=''):
        try:
            time.sleep(10)

            prompt = """ 
            you are @aixbt_agent, an ai agent assigned to make reply tweets by representing @aixbt_agent twitter account which is the official page of Exmplr

            Analyze the data below and make a reply tweet :

            Exmplr is an AI-driven platform designed to streamline clinical trial data analysis. It uses advanced machine learning techniques to extract, transform, and load data from various sources, converting them into relational entities for comprehensive analysis. This setup allows researchers to quickly search for specific conditions or interventions and obtain instant results.  ￼

            Key features of Exmplr include:
                •	Advanced Data Extraction: Efficiently pulls critical information from numerous studies, simplifying the initial stages of meta-analyses or systematic reviews.  ￼
                •	Relational Entity Correlation: Offers a fresh perspective on data interconnectedness by correlating data as relational entities, providing deeper insights and a more comprehensive understanding of clinical trial data.  ￼
                •	Accelerated Research Progress: Significantly reduces the time required for data collation, extraction, and analysis, bringing researchers closer to their milestones and ensuring timely progress.  ￼

            Exmplr also provides customizable tools and workflows tailored to researchers' unique needs, from literature analysis to data interpretation. The platform adapts to individual workflows, helping streamline tasks, eliminate bottlenecks, and achieve research goals more efficiently.  ￼

            Additionally, Exmplr offers on-premise options to ensure complete control over data, emphasizing privacy and security.

            .

            after analyzing these , make a reply tweet - {} 

            in an informative way

            if the conversation is random, answer in a professional  small talk way.
            If the tweet is about enquiry about our services or anything regarding it, answer after collecting the data from the inofrmation provided above.

            And if the question is related to crypto market or currency, redirect it to @aixbt

            Make sure to only return the reply tweet. nothing else must be added to the returned value.Also dont add any unwanted mentions in the reply tweet.Also Dont add any hashtags in the tweet
            """.format(original_tweet)
            response = self.gen_ai.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-4o",)
            
            contents = response.choices[0].message.content
            content = contents.replace('"',"")
        
            print("Openai Generated reply - \n" + content)
            time.sleep(50)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(60)
            return 'failed'


    def generate_marketing_post(self):
        """Generate a marketing post about $EXMPLR"""
        try:
            time.sleep(10)
            content_type = random.choice(self.content_types)
            
            prompt = f"""
            Generate a Twitter thread (3-4 tweets) about {content_type}.
            
            Key Points:
            - Focus on upcoming features and development milestones
            - Always include $EXMPLR token symbol
            - Make it engaging for global audience
            - End with a call to action
            
            About Exmplr:
            Exmplr is an AI-driven platform for clinical trial data analysis, using advanced ML for data extraction and analysis.
            The platform is developing blockchain integration for enhanced security and transparency.
            Key features include advanced data extraction, relational entity correlation, and accelerated research progress.
            
            Format as a thread with 🧵 emoji at start and number each tweet.
            Don't add any unwanted mentions or hashtags.
            """
            
            response = self.gen_ai.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-4o",)
            
            contents = response.choices[0].message.content
            content = contents.replace('"',"")
        
            print("Generated marketing thread - \n" + content)
            time.sleep(50)
            return content
        
        except Exception as e:
            print(e)
            time.sleep(60)
            return 'failed'
