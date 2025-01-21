from http.client import HTTPException
import os
import logging
import re
import urllib.parse
import random

from pydantic import BaseModel
import openai
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


def contains_pii_or_phi(content: str) -> bool:
    """Detects if the content contains PII or PHI based on stricter patterns."""
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
    """Classify the query into categories using OpenAI."""
    try:
        prompt = f"""
        You are a query classifier for a clinical trial assistant. 
        Classify the following query into one of these categories:
        1. Clinical Trials: Questions about recruitment, trial phases, or related topics.
        2. Generic Healthcare: General healthcare or drug-related questions.
        3. Product Inquiry: Questions about Exmplr's services or offerings.
        4. Live Data: Questions requiring up-to-date information.
        5. Price/Trading: Questions about token price, trading, or market speculation.
        6. Random: Other general questions to the bot
        
        Query: "{query}"
        
        Respond with only one of the following options: "clinical_trials", "generic_healthcare", "product_inquiry", "live_data", "price_trading", or "random".
        If unsure, default to "generic_healthcare".
        """
        response = gen_ai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        classification = response.choices[0].message.content.strip().lower()
        logger.info(f"Classified Query: {query} -> {classification}")
        return classification

    except Exception as e:
        logger.error(f"Error classifying query: {e}")
        return "generic_healthcare"


def extract_condition(query: str) -> str:
    """Extract medical condition using OpenAI."""
    try:
        prompt = f"""
        Extract the medical condition or research topic from this query.
        If multiple conditions are mentioned, select the most specific one.
        If no specific condition is found, return "clinical research".
        
        Query: "{query}"
        
        Examples:
        "Looking for breast cancer trials" -> "breast cancer"
        "Any diabetes studies in New York" -> "diabetes"
        "Help with trial recruitment" -> "clinical research"
        "Studies for Alzheimer's" -> "alzheimers"
        "Parkinson's disease research" -> "parkinsons"
        
        Return only the condition, nothing else.
        """
        response = gen_ai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        condition = response.choices[0].message.content.strip().lower()
        condition = response.choices[0].message.content.strip().lower()
        
        # Normalize common conditions with proper URL formatting
        condition_map = {
            "breast cancer": "BREAST+CANCER",
            "cancer": "CANCER",
            "diabetes": "DIABETES",
            "alzheimer's": "ALZHEIMERS",
            "alzheimers": "ALZHEIMERS",
            "parkinson's": "PARKINSONS",
            "parkinsons": "PARKINSONS",
            "hiv": "HIV",
            "leukemia": "LEUKEMIA",
            "clinical research": "CLINICAL+RESEARCH",
            "clinical trials": "CLINICAL+RESEARCH"
        }
        
        return condition_map.get(condition, condition.upper())
    except Exception as e:
        logger.error(f"Error extracting condition: {e}")
        return "CLINICAL+RESEARCH"


def generate_exmplr_api_payload(query: str, topics: list, context: dict = None) -> dict:
    """Generate Exmplr API payload based on extracted topics and context."""
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
        "recruitment_status": "q26",  # Added recruitment status parameter
    }

    # Initialize empty payload
    payload = {}
    
    # Add recruitment status only for recruitment-related queries
    if any(word in query.lower() for word in ['recruit', 'recruiting', 'recruitment']):
        payload["recruitment_status"] = "Recruiting"
        payload["status_of_study"] = "Recruiting"
    
    # Add condition to search query if provided
    if topics and topics[0] != "CLINICAL+RESEARCH":
        payload["search_query"] = topics[0]
        
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
    """Generate Exmplr link by mapping API payload to query numbers."""
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

    # Construct URL with proper encoding
    base_url = "https://app.exmplr.io/dashboard/details"
    
    # Handle each parameter individually to maintain + in values
    param_parts = []
    for key, value in query_params.items():
        # Replace spaces with + in the value
        encoded_value = str(value).replace(" ", "+")
        # Encode the rest of the value but preserve +
        encoded_value = urllib.parse.quote(encoded_value, safe="+")
        param_parts.append(f"{key}={encoded_value}")
    
    query_string = "&".join(param_parts)
    return f"{base_url}?{query_string}"


def find_enquiry(query):
    """Process a tweet request and route it to the appropriate handler."""
    try:
        genai = Data_generation()
        category = classify_query(query)

        # Check for PII/PHI
        if contains_pii_or_phi(query) and category != 'random':
            response = {
                "response_type": "WARNING",
                "content": (
                    "As per HIPAA guidelines, we cannot respond to questions containing Personally Identifiable Information (PII) or Protected Health Information (PHI). "
                    "We recommend deleting this post to protect your privacy and avoid sharing sensitive details publicly."
                ),
                "link": None
            }
            return response['content']

        # Extract age and condition
        age_match = re.search(r"\b(\d{1,3})\s*(years|yrs)?\s*(old)?", query, re.IGNORECASE)
        age = int(age_match.group(1)) if age_match else None

        # Extract condition using AI
        condition = extract_condition(query)

        # Handle clinical trial requests
        if category == "clinical_trials":
            # Generate payload and link
            topics = [condition]
            context = {"age": age, "location": "United States"}
            api_payload = generate_exmplr_api_payload(query, topics, context)
            link = generate_exmplr_link(api_payload)

            # Condition-specific insights with URL-friendly names
            condition_insights = {
                "BREAST+CANCER": "exploring innovative therapies and personalized approaches",
                "CANCER": "including targeted therapies and immunotherapy",
                "DIABETES": "covering Type 1, Type 2, and novel treatments",
                "HIV": "investigating breakthrough treatments",
                "ALZHEIMERS": "focusing on early detection and treatment",
                "PARKINSONS": "researching neuroprotective strategies",
                "LEUKEMIA": "studying targeted cellular therapies",
                "CLINICAL+RESEARCH": "with comprehensive analysis"
            }

            # Generate response
            age_text = f"patients aged {age}" if age else "patients of all ages"
            insight = condition_insights.get(condition, "with comprehensive analysis")
            
            responses = [
                f"🔍 Discover relevant clinical trials for {condition}, {insight}, targeting {age_text}. Explore detailed insights on our analytics platform:\n{link}",
                f"📊 Access curated {condition} trials {insight}, suitable for {age_text}. Get comprehensive trial data through our platform:\n{link}",
                f"🎯 Looking for {condition} trials? We've found promising studies {insight} for {age_text}. Dive deeper into the data on our platform:\n{link}",
                f"💡 Explore active {condition} research {insight}, matched for {age_text}. Get detailed analytics and insights on our platform:\n{link}",
                f"🔬 Find innovative {condition} trials {insight}, designed for {age_text}. Access in-depth trial information here:\n{link}"
            ]
            
            response = {
                "response_type": "SUCCESS",
                "content": random.choice(responses)
            }
            return response["content"]

        elif category == "generic_healthcare":
            # Generate trial link
            topics = [condition] if condition != "CLINICAL+RESEARCH" else []
            api_payload = generate_exmplr_api_payload(query, topics, {"location": "United States"})
            link = generate_exmplr_link(api_payload)
            
            platform_features = [
                "latest research developments",
                "ongoing clinical trials",
                "research analytics",
                "trial data insights",
                "current studies"
            ]
            
            responses = [
                f"🏥 For medical advice, please consult healthcare professionals. Meanwhile, explore {random.choice(platform_features)} about {condition} on our research platform:\n{link}",
                f"👨‍⚕️ While we recommend consulting medical experts for health advice, you can access {random.choice(platform_features)} related to {condition} here:\n{link}",
                f"🔬 Your health matters - please seek professional medical guidance. In the meantime, discover {random.choice(platform_features)} for {condition} at:\n{link}",
                f"💡 For personalized medical advice, consult healthcare providers. To stay informed about {condition} {random.choice(platform_features)}, visit:\n{link}"
            ]
            
            response = {
                "response_type": "SUCCESS",
                "content": random.choice(responses)
            }
            return response['content']

        elif category == "price_trading":
            base_url = "https://app.exmplr.io"
            responses = [
                f"🤖 For trading insights, please check with @aixbt. Meanwhile, explore how $EXMPLR Agent advances clinical research:\n{base_url}",
                f"📊 Trading questions? @aixbt can help! $EXMPLR Agent focuses on revolutionizing clinical trials:\n{base_url}",
                f"🔬 While @aixbt can assist with trading, $EXMPLR Agent is transforming clinical research. Learn more:\n{base_url}",
                f"🧪 For market analysis, connect with @aixbt. Discover how $EXMPLR Agent empowers clinical research:\n{base_url}",
                f"📈 @aixbt specializes in trading insights. Meanwhile, see how $EXMPLR Agent is advancing DeSci:\n{base_url}"
            ]
            return random.choice(responses)

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

    except Exception as e:
        logger.error(f"General Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
