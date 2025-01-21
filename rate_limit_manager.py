import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from storage_manager import StorageManager

class RateLimitManager:
    def __init__(self, storage_manager: StorageManager):
        self.storage = storage_manager
        self.rate_limits_file = "rate_limits.json"
        self.backoff_schedule = [
            60,      # 1 hour
            240,     # 4 hours
            1440,    # 24 hours
            4320,    # 3 days
            10080    # 7 days
        ]
        self.datetime_format = '%Y-%m-%d %H:%M:%S'

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc or parsed.path

    def _load_json_limits(self) -> Dict:
        """Load rate limits from JSON file (fallback storage)"""
        try:
            if os.path.exists(self.rate_limits_file):
                with open(self.rate_limits_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading rate limits from JSON: {e}")
            return {}

    def _save_json_limits(self, limits: Dict) -> None:
        """Save rate limits to JSON file (fallback storage)"""
        try:
            with open(self.rate_limits_file, 'w') as f:
                json.dump(limits, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving rate limits to JSON: {e}")

    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime for Postgres timestamp"""
        return dt.strftime(self.datetime_format)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime"""
        try:
            # Try parsing with timezone info
            if '+' in timestamp_str or 'Z' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Try parsing without timezone info
            return datetime.strptime(timestamp_str, self.datetime_format)
        except ValueError:
            # If all else fails, try parsing ISO format
            return datetime.fromisoformat(timestamp_str)

    async def get_rate_limit(self, url: str) -> Optional[Dict[str, Any]]:
        """Get rate limit info for a domain"""
        domain = self._get_domain(url)
        try:
            # Try Supabase
            if self.storage.supabase:
                response = self.storage.supabase.table('rate_limits')\
                    .select('*')\
                    .eq('domain', domain)\
                    .execute()
                
                if hasattr(response, 'data'):
                    data = response.data
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                    
        except Exception as e:
            print(f"Error getting rate limit from Supabase: {e}")
        
        # Fallback to JSON
        limits = self._load_json_limits()
        return limits.get(domain)

    async def update_rate_limit(self, url: str, success: bool) -> None:
        """Update rate limit info after an attempt"""
        domain = self._get_domain(url)
        now = datetime.now().astimezone()
        
        try:
            # Get current rate limit info
            rate_limit = await self.get_rate_limit(url)
            
            if rate_limit:
                # Update existing rate limit
                consecutive_failures = 0 if success else rate_limit['consecutive_failures'] + 1
                backoff_idx = min(consecutive_failures, len(self.backoff_schedule) - 1)
                backoff_period = self.backoff_schedule[backoff_idx] if not success else 0
                
                next_retry = (now if success else now + timedelta(minutes=backoff_period))
                
                data = {
                    'last_attempt_at': self._format_timestamp(now),
                    'success': success,
                    'consecutive_failures': consecutive_failures,
                    'next_retry_at': self._format_timestamp(next_retry),
                    'backoff_period': backoff_period,
                    'updated_at': self._format_timestamp(now)
                }
            else:
                # Create new rate limit entry
                consecutive_failures = 0 if success else 1
                backoff_period = self.backoff_schedule[0] if not success else 0
                next_retry = (now if success else now + timedelta(minutes=backoff_period))
                
                data = {
                    'domain': domain,
                    'last_attempt_at': self._format_timestamp(now),
                    'success': success,
                    'consecutive_failures': consecutive_failures,
                    'next_retry_at': self._format_timestamp(next_retry),
                    'backoff_period': backoff_period,
                    'created_at': self._format_timestamp(now),
                    'updated_at': self._format_timestamp(now)
                }
            
            try:
                # Try Supabase
                if self.storage.supabase:
                    if rate_limit:
                        response = self.storage.supabase.table('rate_limits')\
                            .update(data)\
                            .eq('domain', domain)\
                            .execute()
                    else:
                        response = self.storage.supabase.table('rate_limits')\
                            .insert(data)\
                            .execute()
                    
                    if not hasattr(response, 'data'):
                        raise Exception("No response data from Supabase")
                        
            except Exception as e:
                print(f"Error updating rate limit in Supabase: {e}")
                # Fallback to JSON
                limits = self._load_json_limits()
                limits[domain] = data
                self._save_json_limits(limits)
                
        except Exception as e:
            print(f"Error updating rate limit: {e}")

    async def can_access(self, url: str) -> bool:
        """Check if a domain can be accessed"""
        try:
            rate_limit = await self.get_rate_limit(url)
            if not rate_limit:
                return True
            
            if rate_limit['success']:
                return True
                
            now = datetime.now().astimezone()
            next_retry = self._parse_timestamp(rate_limit['next_retry_at'])
            if next_retry.tzinfo is None:
                next_retry = next_retry.replace(tzinfo=now.tzinfo)
            
            return now >= next_retry
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return True  # Allow access on error

    async def record_success(self, url: str) -> None:
        """Record a successful access attempt"""
        await self.update_rate_limit(url, True)

    async def record_failure(self, url: str) -> None:
        """Record a failed access attempt"""
        await self.update_rate_limit(url, False)

    def get_backoff_time(self, consecutive_failures: int) -> int:
        """Get backoff time in minutes for number of failures"""
        idx = min(consecutive_failures, len(self.backoff_schedule) - 1)
        return self.backoff_schedule[idx]