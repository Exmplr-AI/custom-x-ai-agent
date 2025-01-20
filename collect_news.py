import feedparser



def collect_initial_news(links):
    
    
    latest_feeds = {}
    for link in links:
        feed = feedparser.parse(link)

    # Print the latest feed entry
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            url =latest_entry.link
            summary =  latest_entry.summary
            total = {'title':title,'summary':summary,'url':url}
            latest_feeds[link] = total
        else:
            print("No entries found in the feed.")
        
    return latest_feeds



def check_latest_feed(url,data):
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            link =latest_entry.link
            summary =  latest_entry.summary
            total = {'title':title,'summary':summary,'url':link}
        if data == total:
            return None
        else:
            return total
    except Exception as e:
        print(e)
        return None