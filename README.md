# $EXMPLR Social Media Bot

Automated content generation and posting system for $EXMPLR token and platform marketing.

## Features

- Enhanced Content Generation:
  * 6-7 daily marketing posts for global coverage
  * Data-driven insights with specific metrics
  * Technical accuracy focus
  * Real-world impact measurements

- Improved News Processing:
  * Three-step validation system
  * Smart relevance filtering
  * Clear status tracking
  * Detailed processing logs

- Robust Scheduling:
  * Marketing posts every 3.5 hours
  * News checks every 50 minutes
  * Quick 15-minute initial post
  * Optimal global timezone coverage

- Advanced Analytics:
  * Comprehensive validation logging
  * Article processing tracking
  * Queue status monitoring
  * Performance metrics
  * Engagement analytics

- Technical Improvements:
  * Async/await optimization
  * Enhanced error handling
  * Proper rate limiting
  * Database efficiency

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Set up Google Custom Search API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Custom Search API
   - Create API credentials (API key)
   - Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Create a new search engine
   - Get your Search Engine ID
   - Configure search engine settings for your needs

3. Set up Supabase:
   - Create a project at [Supabase](https://supabase.com)
   - Get your project URL and anon key
   - Run the provided `db_setup.sql` script in Supabase SQL editor
   - Configure RLS (Row Level Security) policies as needed
   - Set up automated backups

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in all required credentials:
```bash
# Twitter API Credentials
api_key=your_twitter_api_key
api_secret=your_twitter_api_secret
bearer=your_twitter_bearer_token
access=your_twitter_access_token
access_secret=your_twitter_access_secret

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# Google Custom Search API
GOOGLE_API_KEY=your_google_api_key
SEARCH_ENGINE_ID=your_custom_search_engine_id

# Supabase Configuration
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key

# Optional: Timezone (defaults to America/Chicago)
TIMEZONE=America/Chicago
```

## Data Storage & Analytics

The bot utilizes Supabase for robust data management and analytics:

### Stored Data
- Tweet interactions and responses
- Research analysis results
- News monitoring data
- Rate limit tracking
- Performance metrics
- Content generation history

### Analytics Capabilities
- Engagement tracking
- Response time analysis
- Content performance metrics
- API usage optimization
- Rate limit monitoring
- Historical trend analysis

### Tables
1. interactions
   - Stores all bot interactions with timestamps
   - Tracks response types and timing
   - Maintains context history
   - Optimized indexes for fast querying
   - Full RLS policy protection

2. research_cache
   - Stores analyzed research content
   - Maintains topic relationships
   - Tracks content performance
   - Automatic expiration handling
   - Efficient caching system

3. article_queue
   - Smart scheduling system
   - 5-minute initial post timing
   - 50-minute spacing for subsequent posts
   - Status tracking (queued, posted, failed)
   - Error message logging
   - Optimized scheduling indexes

### Security & Performance
- Row Level Security (RLS) policies
- Service role access controls
- Proper permission grants
- Optimized indexes for common queries
- Efficient timestamp handling
- Robust error recovery

## Posting Schedule

The bot maintains the following posting schedule:

### Daily Posts
1. Marketing Posts (6-7x daily):
   - Every 3.5 hours for optimal global coverage
   - First post 15 minutes after startup
   - Enhanced content quality with specific metrics
   - Technical accuracy and real-world impact focus
   - Data-driven insights and achievements

2. News Updates:
   - 50-minute intervals between checks
   - Three-step validation process:
     * Relevance check for EXMPLR features
     * Content quality assessment
     * Queue status verification
   - Detailed logging of article processing
   - Smart filtering with clear status tracking

3. Community Engagement:
   - Fast initial setup (1 minute)
   - Mention checks every 5 minutes
   - News analysis every 10 minutes
   - Improved async handling
   - Enhanced error recovery
   - Clear validation logging

### Weekly Posts
1. Long-Form Research Content (Wednesdays):
   - In-depth analysis of rotating topics:
     * AI in Clinical Research
     * Decentralized Science
     * AI for Drug Discovery
   - Comprehensive thread format
   - Data-backed insights
   - Industry trends and analysis

## Running the Bot

Start the bot:
```bash
python3 main.py
```

The system automatically manages all posting schedules and interactions while maintaining proper $EXMPLR branding.

## Content Types

1. Marketing Posts:
- Feature Previews with Metrics: "reduces analysis time by 60%"
- Technical Architecture: "processes 1M+ data points daily"
- Development Updates: "achieves 99.9% accuracy"
- Research Impact: "cuts trial setup time by 45%"
- Blockchain Integration: "ensures 100% data integrity"
- Platform Features: Real-time capabilities and improvements
- Community Insights: User success stories and applications
- Vision & Roadmap: Strategic development plans

2. Research Posts:
- AI in Clinical Research: Latest breakthroughs and applications
- Decentralized Science: Industry trends and adoption
- Drug Discovery Innovation: AI-powered methodologies
- Healthcare Automation: Efficiency improvements
- Data Analysis: Real-world impact metrics

3. News & Updates:
- Industry News: Smart relevance filtering
- Clinical Trial Updates: Real-time monitoring
- Technology Developments: Impact assessment
- Research Breakthroughs: Validation process
- Market Analysis: Data-driven insights

## Production Deployment

For production deployment:
1. Update all environment variables
2. Set up process monitoring (e.g., supervisor, systemd)
3. Configure logging
4. Set up error notifications
5. Monitor API rate limits
6. Configure Supabase backup schedule
7. Set up monitoring for database performance

## Maintenance

- Monitor Twitter API rate limits
- Keep API keys updated
- Review and update content strategies
- Monitor engagement metrics
- Update research topics as needed
- Regular database maintenance:
  * Review and optimize queries
  * Monitor storage usage
  * Maintain backup integrity
  * Clean up old data as needed
  * Monitor RLS policies