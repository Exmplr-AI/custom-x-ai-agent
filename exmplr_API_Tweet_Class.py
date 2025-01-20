from http.client import HTTPException
import os
import logging
import re
import urllib.parse
import random

from pydantic import BaseModel
from openai import OpenAI
from ai_data import Data_generation


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()
# Load OpenAI API key from environment

gen_ai = OpenAI(
            
        api_key=os.getenv('OPENAI_API_KEY')
        
        )



# Define Models
class TweetRequest(BaseModel):
    tweet_id: str
    content: str
    author: str
    author_bio: str = None


# Helper Functions
def contains_pii_or_phi(content: str) -> bool:
    """
    Detects if the content contains PII or PHI based on stricter patterns.
    """
    pii_patterns = [
        r"\bmy name is\b",  # Self-identifying with name
        r"\bi am\b",  # Statements like "I am 35" or "I have cancer"
        r"\bi have\b",  # Explicitly describing their own condition
    ]
    for pattern in pii_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning(f"Detected potential PII/PHI in content: {content}")
            return True
    return False


def classify_query(query: str) -> str:
    """
    Classify the query into categories like clinical_trials, generic_healthcare, product_inquiry, live_data.
    """
    try:
        prompt = f"""
        You are a query classifier for a clinical trial assistant. 
        Classify the following query into one of these categories:
        1. Clinical Trials: Questions about recruitment, trial phases, or related topics.
        2. Generic Healthcare: General healthcare or drug-related questions.
        3. Product Inquiry: Questions about Exmplr's services or offerings.
        4. Live Data: Questions requiring up-to-date information.
        5. Random : question other than health care. simple questions to the bot
        Query: "{query}"
        
        Respond with only one of the following options: "clinical_trials", "generic_healthcare", "product_inquiry", or "live_data".
        If unsure, default to "generic_healthcare".
        """
        response = gen_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        classification = response.choices[0].message.content.strip().lower()
        logger.info(f"Classified Query: {query} -> {classification}")
        return classification

    except Exception as e:
        logger.error(f"Error classifying query: {e}")
        return "generic_healthcare"


def generate_exmplr_api_payload(query: str, topics: list, context: dict = None) -> dict:
    """
    Generate Exmplr API payload based on extracted topics and context.
    """
    query_param_map = {
        "search_query": "q1",
        "age_from": "q2",
        "age_to": "q3",
        "gender": "q4",
        "race": "q5",
        "ethnicity": "q6",
        "intervention_type": "q7",
        "location": "q8",
        "study_posted_from_year": "q9",
        "study_posted_to_year": "q10",
        "allocation": "q11",
        "sponsor_type": "q12",
        "sponsor": "q13",
        "show_only_results": "q14",
        "phase": "q20",
        "status_of_study": "q21",
    }

    payload = {}

    # Map condition to "search_query"
    condition_map = {
        "cancer": "CANCER",
        "diabetes": "DIABETES",
        "alzheimer": "ALZHEIMER'S DISEASE",
        "leukemia": "LEUKEMIA",
        "hiv": "HIV",
        "covid": "COVID-19",
    }
    for topic in topics:
        if topic.lower() in condition_map:
            payload["search_query"] = condition_map[topic.lower()]
            break
        
    print(context)
    # Add context-based parameters
    if context:
        if "age" in context and context['age'] != None:
            age = context["age"]
            if age < 18:
                payload["age_from"], payload["age_to"] = "0", "17"
            elif age >= 65:
                payload["age_from"], payload["age_to"] = "65", "100"
            else:
                payload["age_from"], payload["age_to"] = str(max(0, age - 5)), str(age + 5)

        if "location" in context:
            location = context["location"].lower()
            us_cities = ["new york", "los angeles", "chicago", "boston", "california"]
            payload["location"] = "United States" if location in us_cities else location.title()

    return payload


def generate_exmplr_link(api_payload: dict) -> str:
    """
    Generate Exmplr link by mapping API payload to query numbers.
    """
    query_param_map = {
        "search_query": "q1",
        "age_from": "q2",
        "age_to": "q3",
        "gender": "q4",
        "race": "q5",
        "ethnicity": "q6",
        "intervention_type": "q7",
        "location": "q8",
        "study_posted_from_year": "q9",
        "study_posted_to_year": "q10",
        "allocation": "q11",
        "sponsor_type": "q12",
        "sponsor": "q13",
        "show_only_results": "q14",
        "phase": "q20",
        "status_of_study": "q21",
    }

    # Map API payload keys to query numbers
    query_params = {
        query_param_map[key]: value
        for key, value in api_payload.items()
        if key in query_param_map and value is not None
    }

    # Construct the URL
    base_url = "https://app.exmplr.io/dashboard/details"
    encoded_query = urllib.parse.urlencode(query_params)
    return f"{base_url}?{encoded_query}"


# @app.post("/api/v1/process_tweet")
# async def process_tweet(request: TweetRequest):
def find_enquiry(query):
    """
    Process a tweet request and route it to the appropriate handler based on query classification.
    """
    try:
        
        genai = Data_generation()
        category = classify_query(query)

        # Check for PII/PHI
        if contains_pii_or_phi(query) and category!='random':
            response = {
                "response_type": "WARNING",
                "content": (
                    "As per HIPAA guidelines, we cannot respond to questions containing Personally Identifiable Information (PII) or Protected Health Information (PHI). "
                    "We recommend deleting this post to protect your privacy and avoid sharing sensitive details publicly."
                ),
                "link": None
            }
            return response['content']

        # Classify the query
        category = classify_query(query)
        print(category)

        # Handle clinical trial requests
        if category == "clinical_trials":
            # Extract age and condition from the query
            age_match = re.search(r"\b(\d{1,3})\s*(years|yrs)?\s*(old)?", query, re.IGNORECASE)
            age = int(age_match.group(1)) if age_match else None

            condition_match = re.search(r"(breast cancer|cancer|diabetes|HIV|Alzheimer's|Parkinson's)", query, re.IGNORECASE)
            condition = condition_match.group(1) if condition_match else "unspecified condition"

            # Generate Exmplr payload and link
            topics = [condition] if condition else []
            context = {"age": age, "location": "United States"}
            api_payload = generate_exmplr_api_payload(query, topics, context)
            link = generate_exmplr_link(api_payload)

            # Generate more engaging response
            age_text = f"patients aged {age}" if age else "patients of all ages"
            responses = [
                f"🔍 Discover relevant clinical trials for {condition.upper()} targeting {age_text}. Explore detailed insights on our analytics platform:\n{link}",
                f"📊 We've found clinical trials for {condition.upper()} suitable for {age_text}. Access comprehensive trial data through our insights platform:\n{link}",
                f"🎯 Looking for {condition.upper()} clinical trials? We've curated trials suitable for {age_text}. Dive deeper into the data on our insights platform:\n{link}",
                f"💡 Explore curated clinical trials for {condition.upper()} ({age_text}). Get detailed analytics and insights on our platform:\n{link}"
            ]
            
            response = {
                "response_type": "SUCCESS",
                "content": random.choice(responses)
            }
            return response["content"]

        elif category == "generic_healthcare":
            responses = [
                "While we focus on clinical trial analytics, we recommend consulting healthcare providers for personalized medical advice. Learn more about our data insights platform at app.exmplr.io",
                "For medical advice, please consult qualified healthcare professionals. To explore clinical trial data and research insights, visit our platform at app.exmplr.io",
                "Your health is important - please seek professional medical guidance. Meanwhile, discover clinical research insights on our platform at app.exmplr.io",
                "We recommend consulting healthcare professionals for medical advice. Explore clinical trial analytics and research data on our platform at app.exmplr.io"
            ]
            response = {
                "response_type": "SUCCESS",
                "content": random.choice(responses)
            }
            return response['content']

        elif category == "product_inquiry":
            response = genai.make_a_reply(query)
            return response
        elif category == 'random':
            response = genai.make_a_reply(query)
            return response

        else:
            logger.warning(f"Unrecognized category '{category}'. Defaulting to product inquiry.")
            response = genai.make_a_reply(query)
            
            return response
        
        return response

    except Exception as e:
        logger.error(f"General Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
