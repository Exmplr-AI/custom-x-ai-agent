import feedparser
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_initial_news(links):
    """Collect the latest entries from each feed"""
    latest_feeds = {}
    for link in links:
        try:
            feed = feedparser.parse(link)
            if feed.entries:
                # Store only the latest entry for each feed
                latest_entry = feed.entries[0]
                entry_data = {
                    'title': latest_entry.title,
                    'summary': latest_entry.summary,
                    'url': latest_entry.link
                }
                latest_feeds[link] = [entry_data]  # Keep as list for consistency
                logger.info(f"Collected latest entry from {link}: {entry_data['title']}")
            else:
                logger.warning(f"No entries found in feed: {link}")
        except Exception as e:
            logger.error(f"Error collecting from feed {link}: {str(e)}")
    
    return latest_feeds

def check_latest_feed(url, previous_entries):
    """Check for new entries in a feed and return all new articles"""
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            logger.warning(f"No entries found in feed: {url}")
            return None

        # Check all entries for new content
        new_entries = []
        for entry in feed.entries:  # Check all entries
            entry_data = {
                'title': entry.title,
                'summary': entry.summary,
                'url': entry.link
            }
            
            # Check if this entry is new
            is_new = True
            if previous_entries:  # Only check if we have previous entries
                for prev_entry in previous_entries:
                    if (prev_entry['title'] == entry_data['title'] and
                        prev_entry['url'] == entry_data['url']):
                        is_new = False
                        break
            
            if is_new:
                logger.info(f"Found new article: {entry_data['title']}")
                new_entries.append(entry_data)

        if new_entries:
            logger.info(f"Found {len(new_entries)} new articles in {url}")
            return new_entries
        else:
            logger.info(f"No new articles found in {url}")
            return None

    except Exception as e:
        logger.error(f"Error checking feed {url}: {str(e)}")
        return None