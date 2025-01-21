# $EXMPLR Social Media Bot

Automated content generation and posting system for $EXMPLR token and platform marketing.

## Features

- Automated Twitter interactions and responses
- 24/7 global marketing content generation
- Research content analysis and posting
- News monitoring and updates
- Proper $EXMPLR token mentions
- Smart handling of mentions and replies
- Comprehensive data storage and analytics with Supabase
- Rate limit management and optimization
- Interaction history tracking
- Performance analytics and insights

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
   - Stores all bot interactions
   - Tracks response types and timing
   - Maintains context history

2. rate_limits
   - Monitors API usage
   - Tracks endpoint limits
   - Optimizes request timing

3. research_data
   - Stores analyzed research content
   - Maintains topic relationships
   - Tracks content performance

## Posting Schedule

The bot maintains the following posting schedule:

### Daily Posts
1. Marketing Posts (3x daily):
   - Random times across 24 hours for global coverage
   - Focus on $EXMPLR features, roadmap, and development
   - Short, engaging content with calls to action

2. News Updates (~every 50 minutes):
   - Industry news analysis
   - Clinical trial updates
   - Technology developments
   - Relevant market updates

3. Community Engagement:
   - Continuous monitoring of mentions
   - Smart responses to queries
   - Community interaction

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
- Feature previews
- Roadmap updates
- Community discussions
- Vision stories
- Development updates
- Use case previews
- Technical previews
- Global impact discussions

2. Research Posts:
- AI in Clinical Research
- Decentralized Science
- AI for Drug Discovery

3. News & Updates:
- Industry news
- Clinical trial updates
- Technology developments

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