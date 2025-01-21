import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in the cache with TTL in seconds"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entries
            oldest = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])[:-900]
            for k, _ in oldest:
                del self.cache[k]

        self.cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'expires': time.time() + ttl
        }

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache"""
        if key in self.cache:
            data = self.cache[key]
            if data['expires'] > time.time():
                return data['value']
            del self.cache[key]
        return None

class JSONStorageHandler:
    def __init__(self):
        self.interactions_file = "interactions.json"
        self.research_file = "research_cache.json"

    def _load_json(self, filename: str, default: Any) -> Any:
        """Load data from a JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return json.load(f)
            return default
        except Exception as e:
            print(f"Error loading JSON file {filename}: {e}")
            return default

    def _save_json(self, filename: str, data: Any) -> None:
        """Save data to a JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving JSON file {filename}: {e}")

    async def store_interaction(self, data: Dict) -> None:
        """Store an interaction in JSON file"""
        interactions = self._load_json(self.interactions_file, [])
        interactions.append({
            **data,
            'stored_at': datetime.now().isoformat()
        })
        # Keep last 1000 interactions
        self._save_json(self.interactions_file, interactions[-1000:])

    async def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions from JSON file"""
        interactions = self._load_json(self.interactions_file, [])
        return interactions[-limit:]

    async def store_research(self, data: Dict) -> None:
        """Store research data in JSON file"""
        research = self._load_json(self.research_file, [])
        research.append({
            **data,
            'stored_at': datetime.now().isoformat()
        })
        self._save_json(self.research_file, research)

class StorageManager:
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self.json_fallback = JSONStorageHandler()
            self.memory_cache = MemoryCache()
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            self.supabase = None
            self.json_fallback = JSONStorageHandler()
            self.memory_cache = MemoryCache()

    async def store_interaction(self, data: Dict) -> None:
        """Store an interaction with fallback handling"""
        try:
            # Try memory cache first
            cache_key = f"interaction_{data.get('tweet_id')}"
            self.memory_cache.set(cache_key, data)
            
            # Try Supabase if available
            if self.supabase:
                response = self.supabase.table('interactions').insert(data).execute()
                if hasattr(response, 'data'):
                    return
                
        except Exception as e:
            print(f"Supabase storage failed: {e}")
        
        # Fallback to JSON
        await self.json_fallback.store_interaction(data)

    async def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions with fallback handling"""
        try:
            # Try Supabase if available
            if self.supabase:
                response = self.supabase.table('interactions')\
                    .select('*')\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
                if hasattr(response, 'data'):
                    return response.data
                
        except Exception as e:
            print(f"Supabase query failed: {e}")
        
        # Fallback to JSON
        return await self.json_fallback.get_recent_interactions(limit)

    async def store_research(self, topic: str, content: str, expires_at: str) -> None:
        """Store research data with fallback handling"""
        data = {
            'topic': topic,
            'content': content,
            'summary': content[:250] if content else None,  # Store first 250 chars as summary
            'expires_at': expires_at,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Cache in memory
            cache_key = f"research_{topic}"
            self.memory_cache.set(cache_key, data)
            
            # Store in Supabase if available
            if self.supabase:
                response = self.supabase.table('research_cache').insert(data).execute()
                if hasattr(response, 'data'):
                    return
                
        except Exception as e:
            print(f"Supabase storage failed: {e}")
        
        # Fallback to JSON
        await self.json_fallback.store_research(data)

    async def get_research(self, topic: str) -> Optional[Dict]:
        """Get research data with fallback handling"""
        # Try memory cache first
        cache_key = f"research_{topic}"
        cached_data = self.memory_cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            # Try Supabase if available
            if self.supabase:
                response = self.supabase.table('research_cache')\
                    .select('*')\
                    .eq('topic', topic)\
                    .order('created_at', desc=True)\
                    .limit(1)\
                    .execute()
                
                if hasattr(response, 'data') and response.data:
                    # Update memory cache
                    self.memory_cache.set(cache_key, response.data[0])
                    return response.data[0]
                    
        except Exception as e:
            print(f"Supabase query failed: {e}")
        
        return None

    def format_timestamp(self, dt: datetime) -> str:
        """Format datetime to RFC3339 format for Supabase"""
        return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    async def queue_article(self, title: str, url: str, tweet_content: str, source_feed: str, is_weekly: bool = False) -> bool:
        """Queue an article for posting"""
        try:
            if not self.supabase:
                print("Supabase not available for article queuing")
                return False

            current_time = datetime.now(timezone.utc)
            scheduled_for = current_time + timedelta(minutes=50)

            # Get last scheduled article
            last_article = self.supabase.table('article_queue')\
                .select('scheduled_for')\
                .eq('status', 'queued')\
                .order('scheduled_for', desc=True)\
                .limit(1)\
                .execute()

            if hasattr(last_article, 'data') and last_article.data:
                try:
                    last_scheduled = datetime.strptime(
                        last_article.data[0]['scheduled_for'],
                        '%Y-%m-%dT%H:%M:%S.%fZ'
                    ).replace(tzinfo=timezone.utc)
                    scheduled_for = max(
                        last_scheduled + timedelta(minutes=50),
                        scheduled_for
                    )
                except Exception as e:
                    print(f"Error parsing last scheduled time: {e}")

            # Queue the article
            data = {
                'title': title,
                'url': url,
                'tweet_content': tweet_content,
                'source_feed': source_feed,
                'is_weekly': is_weekly,
                'scheduled_for': self.format_timestamp(scheduled_for),
                'status': 'queued'
            }
            
            response = self.supabase.table('article_queue').insert(data).execute()
            if hasattr(response, 'data'):
                print(f"Article queued for {data['scheduled_for']}")
                return True

        except Exception as e:
            print(f"Error queuing article: {e}")
        
        return False

    async def get_next_article(self) -> Optional[Dict]:
        """Get the next article that's ready to be posted"""
        try:
            if not self.supabase:
                return None

            current_time = self.format_timestamp(datetime.now(timezone.utc))
            
            # Get next scheduled article
            response = self.supabase.table('article_queue')\
                .select('*')\
                .eq('status', 'queued')\
                .lte('scheduled_for', current_time)\
                .order('scheduled_for')\
                .limit(1)\
                .execute()

            if hasattr(response, 'data') and response.data:
                return response.data[0]

        except Exception as e:
            print(f"Error getting next article: {e}")
        
        return None

    async def mark_article_posted(self, article_id: int) -> bool:
        """Mark an article as posted"""
        try:
            if not self.supabase:
                return False

            data = {
                'status': 'posted',
                'posted_at': self.format_timestamp(datetime.now(timezone.utc))
            }
            
            response = self.supabase.table('article_queue')\
                .update(data)\
                .eq('id', article_id)\
                .execute()
                
            if hasattr(response, 'data'):
                return True

        except Exception as e:
            print(f"Error marking article as posted: {e}")
        
        return False

    async def mark_article_failed(self, article_id: int, error_message: str) -> bool:
        """Mark an article as failed"""
        try:
            if not self.supabase:
                return False

            data = {
                'status': 'failed',
                'error_message': error_message
            }
            
            response = self.supabase.table('article_queue')\
                .update(data)\
                .eq('id', article_id)\
                .execute()
                
            if hasattr(response, 'data'):
                return True

        except Exception as e:
            print(f"Error marking article as failed: {e}")
        
        return False