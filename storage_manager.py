import os
import json
import time
from datetime import datetime
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
            'expires_at': expires_at,
            'created_at': datetime.now().isoformat()
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

# Example usage:
"""
storage = StorageManager()

# Store an interaction
await storage.store_interaction({
    'tweet_id': '123456',
    'query_text': 'Looking for diabetes trials',
    'query_type': 'clinical_trials',
    'response_text': 'Here are some trials...',
    'created_at': datetime.now().isoformat()
})

# Get recent interactions
recent = await storage.get_recent_interactions(5)

# Store research
await storage.store_research(
    'diabetes_trials',
    'Latest research on diabetes trials...',
    (datetime.now() + timedelta(days=1)).isoformat()
)

# Get research
research = await storage.get_research('diabetes_trials')
"""