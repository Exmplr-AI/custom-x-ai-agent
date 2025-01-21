"""
Configuration for news sources used by the agent.
All sources have been tested and verified working.
Last tested: 2025-01-21
"""

# RSS Feeds - Verified Working
RSS_FEEDS = {
    "research": [
        # Academic and Research
        # PubMed Feeds
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1puh2wJZbabDSaexjIHnmQiSza4yAs7w5fFmnyzJXgjtz87MqY/?limit=15&utm_campaign=pubmed-2&fc=20240319133207",  # General Clinical Trials
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1x7FOCOHd9PPmKZlDTIbFGLVRxEeF5HdPEAjPOcyhYdMcFokaL/?limit=15&utm_campaign=pubmed-2&fc=20250121105614",  # Custom Clinical Trials
        "http://export.arxiv.org/rss/cs.AI",  # ArXiv AI
        "https://www.nature.com/nm.rss",  # Nature Medicine
        "https://www.cell.com/cell/current.rss",  # Cell Press
        "http://connect.biorxiv.org/biorxiv_xml.php?subject=all",  # BioRxiv
    ],
    
    "tech_news": [
        # Tech and Industry News
        "https://www.technologyreview.com/feed/",  # MIT Tech Review
        "https://rss.sciencedirect.com/publication/science/09333657",  # ScienceDirect AI
        "https://blog.google/technology/health/rss/",  # Google Health
    ],
    
    "medical_news": [
        # Medical and Clinical News
        "https://www.drugs.com/feeds/clinical_trials.xml",  # Drugs.com Trials
        "https://www.drugs.com/feeds/medical_news.xml",  # Drugs.com News
        "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml",  # FDA Biologics
    ]
}

# Google Custom Search Sites - Verified Working
SEARCH_SITES = [
    "clinicaltrials.gov",
    "healthcareitnews.com",
    "mobihealthnews.com"
]

# Search Configurations
SEARCH_QUERIES = [
    "AI clinical trials",
    "healthcare AI innovation",
    "clinical research AI",
    "medical AI breakthrough",
    "AI drug discovery",
    "healthcare automation AI",
    "clinical trial automation",
    "AI medical diagnosis",
    "AI healthcare analytics",
    "medical research AI"
]

def get_search_query(site):
    """Generate search query for Google Custom Search"""
    return f"site:{site} ({' OR '.join(SEARCH_QUERIES)})"

# Feed Categories for Different Post Types
FEED_CATEGORIES = {
    "daily_news": RSS_FEEDS["tech_news"] + RSS_FEEDS["medical_news"],
    "research_content": RSS_FEEDS["research"],
    "all_feeds": (
        RSS_FEEDS["research"] +
        RSS_FEEDS["tech_news"] +
        RSS_FEEDS["medical_news"]
    )
}

# Rate Limiting Configuration
RATE_LIMITS = {
    "rss_feeds": {
        "requests_per_minute": 30,
        "minimum_interval": 60  # seconds between checks for the same feed
    },
    "google_search": {
        "requests_per_day": 100,
        "minimum_interval": 300  # seconds between searches
    }
}

# Content Freshness Settings
CONTENT_AGE_LIMITS = {
    "news": 24,        # hours
    "research": 168,   # hours (1 week)
    "evergreen": 720   # hours (30 days)
}