# Storage System Documentation

## Overview
The storage system implements a three-tier architecture for data persistence:
1. Memory Cache (Primary/Fastest)
2. Supabase Database (Secondary/Persistent)
3. JSON Files (Fallback/Offline)

## Configuration
Required environment variables:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Database Schema
Two main tables:

### interactions
- Stores user interactions and responses
- Fields:
  * id (UUID)
  * tweet_id (VARCHAR)
  * query_text (TEXT)
  * query_type (VARCHAR)
  * response_text (TEXT)
  * created_at (TIMESTAMPTZ)

### research_cache
- Stores research content with expiration
- Fields:
  * id (UUID)
  * topic (VARCHAR)
  * content (TEXT)
  * created_at (TIMESTAMPTZ)
  * expires_at (TIMESTAMPTZ)

## Usage Examples

### Storing Interactions
```python
await storage.store_interaction({
    'tweet_id': '123456',
    'query_text': 'Looking for diabetes trials',
    'query_type': 'clinical_trials',
    'response_text': 'Here are some trials...',
    'created_at': datetime.now().isoformat()
})
```

### Retrieving Research
```python
research = await storage.get_research('diabetes_trials')
if research:
    content = research['content']
```

## Fallback System
The system automatically falls back to JSON file storage if:
1. Supabase connection fails
2. Database operations fail
3. Invalid credentials

JSON files:
- interactions.json: Stores last 1000 interactions
- research_cache.json: Stores research content

## Memory Cache
- Implements TTL (Time To Live)
- Maximum size: 1000 entries
- LRU (Least Recently Used) eviction policy
- Automatic cleanup of expired entries

## Error Handling
1. Database Errors:
   - Graceful fallback to JSON storage
   - Error logging
   - Continued operation

2. File System Errors:
   - Error logging
   - Default empty responses

3. Memory Cache:
   - Automatic cleanup
   - Size management
   - TTL enforcement

## Best Practices
1. Always use async/await with storage operations
2. Check for None returns on get operations
3. Include created_at timestamps
4. Use proper error handling

## Maintenance
1. Monitor JSON file sizes
2. Regularly clean up expired research
3. Check database connection status
4. Monitor memory cache performance