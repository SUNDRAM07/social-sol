"""
AI-powered trending topics service using Groq API
Generates trending topics across different categories with caching
Supports popup functionality when clicking on trending topics
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TrendingTopicsService:
    """Service for generating AI-powered trending topics"""
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.cache_file = "trending_topics_cache.json"
        self.cache_duration_hours = 4
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"
        
        self.categories = {
            "all": "All",
            "technology": "Technology",
            "business": "Business", 
            "lifestyle": "Lifestyle",
            "entertainment": "Entertainment",
            "news": "News"
        }
        
    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        return bool(self.groq_api_key)
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached trending topics"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                # Check if cache is still valid
                cached_at = datetime.fromisoformat(cache_data.get('cached_at', ''))
                if datetime.now() - cached_at < timedelta(hours=self.cache_duration_hours):
                    logger.info(f"Using cached trending topics from {cached_at}")
                    return cache_data
                else:
                    logger.info(f"Cache expired (cached at {cached_at}), will generate fresh topics")
                    
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
        
        return None
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save trending topics to cache"""
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'topics': data
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.info("Trending topics cached successfully")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _generate_topics_with_groq(self) -> Dict[str, List[str]]:
        """Generate trending topics using Groq API"""
        if not self.groq_api_key:
            raise Exception("Groq API key not configured")
        
        current_date = datetime.now().strftime("%B %Y")
        current_season = self._get_current_season()
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        
        # Comprehensive prompt for generating trending topics
        prompt = f"""Generate exactly 25 current trending topics for {current_date} ({current_season}) that are perfect for social media content creation.

CRITICAL: Return ONLY valid JSON. No markdown, no explanations, no extra text. Just the JSON object.

Required format (exactly 5 topics per category):
{{
  "technology": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "business": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "lifestyle": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "entertainment": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "news": ["topic1", "topic2", "topic3", "topic4", "topic5"]
}}

Requirements for each topic:
- Be specific and actionable (not generic)
- Reflect current trends and events in {current_date}
- Be perfect for creating engaging social media posts
- Be relevant to {current_season} season when applicable
- Each topic should be 3-8 words maximum
- Focus on what's actually trending NOW

Categories and examples:
- Technology: AI tools, new apps, tech reviews, digital trends
- Business: entrepreneurship tips, market trends, productivity hacks
- Lifestyle: wellness trends, home improvement, seasonal activities  
- Entertainment: trending shows, viral challenges, celebrity news
- News: current events, social movements, breaking developments

Generate topics that content creators would want to post about RIGHT NOW in {current_date}."""

        data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert social media trend analyst. Always respond with valid JSON only. Do not include any text before or after the JSON."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "model": "llama-3.1-8b-instant",
            "max_tokens": 1000,
            "temperature": 0.8,
        }
        
        try:
            # Make request with better error handling
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60,  # Increased timeout
                stream=False  # Ensure we get the complete response
            )
            
            # Ensure we read the complete response
            response.raise_for_status()
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                logger.info(f"Raw Groq API response length: {len(content)} characters")
                logger.debug(f"Raw content preview: {content[:500]}...")
                
                # Clean the content to extract only JSON
                content = self._clean_json_response(content)
                logger.info(f"Cleaned JSON length: {len(content)} characters")
                
                # Try to parse JSON response with retry logic
                topics_data = self._parse_json_with_retry(content)
                if topics_data:
                    logger.info("Successfully generated trending topics with Groq API")
                    return topics_data
                else:
                    logger.error("Failed to parse JSON after cleaning and retries")
                    logger.error(f"Raw response: {content}")
                    raise Exception("Invalid JSON response from AI")
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                raise Exception(f"Groq API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when calling Groq API: {e}")
            raise Exception(f"Network error: {e}")
    
    def _clean_json_response(self, content: str) -> str:
        """Clean AI response to extract valid JSON"""
        import re
        
        # Remove any text before the first {
        start_idx = content.find('{')
        if start_idx > 0:
            content = content[start_idx:]
        
        # Find the last } and remove anything after it
        end_idx = content.rfind('}')
        if end_idx >= 0:
            content = content[:end_idx + 1]
        
        # Remove any markdown code block markers
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _parse_json_with_retry(self, content: str, max_retries: int = 3) -> Optional[Dict[str, List[str]]]:
        """Parse JSON with retry logic and validation"""
        for attempt in range(max_retries):
            try:
                topics_data = json.loads(content)
                
                # Validate the structure
                if self._validate_topics_structure(topics_data):
                    return topics_data
                else:
                    logger.warning(f"Invalid topics structure on attempt {attempt + 1}")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    # Try to fix common JSON issues
                    content = self._fix_common_json_issues(content)
                else:
                    logger.error(f"All JSON parse attempts failed. Content: {content[:200]}...")
        
        return None
    
    def _validate_topics_structure(self, topics_data: Any) -> bool:
        """Validate that topics data has the expected structure"""
        if not isinstance(topics_data, dict):
            return False
        
        expected_categories = {"technology", "business", "lifestyle", "entertainment", "news"}
        
        # Check if all expected categories are present
        if not expected_categories.issubset(set(topics_data.keys())):
            logger.warning(f"Missing categories. Got: {list(topics_data.keys())}")
            return False
        
        # Check if each category has a list of strings
        for category, topics in topics_data.items():
            if not isinstance(topics, list):
                logger.warning(f"Category {category} is not a list")
                return False
            if not all(isinstance(topic, str) for topic in topics):
                logger.warning(f"Category {category} contains non-string topics")
                return False
            if len(topics) == 0:
                logger.warning(f"Category {category} is empty")
                return False
        
        return True
    
    def _fix_common_json_issues(self, content: str) -> str:
        """Attempt to fix common JSON formatting issues"""
        import re
        
        # Remove trailing commas before } or ]
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        # Ensure proper quote escaping
        content = content.replace('""', '"')
        
        # Remove any incomplete trailing elements
        if content.count('{') > content.count('}'):
            # Find the last complete object
            brace_count = 0
            last_complete_pos = -1
            for i, char in enumerate(content):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_complete_pos = i
            
            if last_complete_pos > 0:
                content = content[:last_complete_pos + 1]
        
        return content
    
    def _get_error_response(self, error_message: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Generate error response when unable to fetch topics"""
        error_topics = {
            "technology": ["Unable to fetch trending topics"],
            "business": ["Unable to fetch trending topics"],
            "lifestyle": ["Unable to fetch trending topics"],
            "entertainment": ["Unable to fetch trending topics"],
            "news": ["Unable to fetch trending topics"]
        }
        
        # Filter by category if specified
        if category and category != "all" and category in error_topics:
            filtered_topics = {category: error_topics[category]}
        else:
            filtered_topics = error_topics
            
        return {
            "success": False,
            "topics": filtered_topics,
            "categories": self.categories,
            "generated_at": datetime.now().isoformat(),
            "using_cache": False,
            "total_topics": sum(len(topics_list) for topics_list in filtered_topics.values()),
            "error": error_message,
            "error_state": True
        }
    
    def _get_current_season(self) -> str:
        """Get current season based on month"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"
    
    
    def get_trending_topics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get trending topics, optionally filtered by category"""
        try:
            # Try to load from cache first
            cached_data = self._load_cache()
            if cached_data:
                topics = cached_data['topics']
            else:
                # Generate fresh topics
                if self.is_configured():
                    logger.info("Generating fresh trending topics with Groq API")
                    topics = self._generate_topics_with_groq()
                    self._save_cache(topics)
                else:
                    logger.warning("Groq API not configured")
                    return self._get_error_response("API not configured - missing GROQ_API_KEY", category)
            
            # Filter by category if specified
            if category and category != "all" and category in topics:
                filtered_topics = {category: topics[category]}
            else:
                filtered_topics = topics
            
            # Add metadata
            return {
                "success": True,
                "topics": filtered_topics,
                "categories": self.categories,
                "generated_at": datetime.now().isoformat(),
                "using_cache": cached_data is not None,
                "total_topics": sum(len(topics_list) for topics_list in filtered_topics.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return self._get_error_response(f"Unable to fetch trending topics: {str(e)}", category)
    
    def refresh_topics(self) -> Dict[str, Any]:
        """Force refresh trending topics (bypass cache)"""
        try:
            # Delete cache file
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("Cache cleared")
            
            # Generate fresh topics
            return self.get_trending_topics()
            
        except Exception as e:
            logger.error(f"Error refreshing topics: {e}")
            return self._get_error_response(f"Unable to refresh trending topics: {str(e)}")
    
    def test_groq_api(self) -> Dict[str, Any]:
        """Test method to debug Groq API responses"""
        try:
            logger.info("Testing Groq API connection and response...")
            topics = self._generate_topics_with_groq()
            return {
                "success": True,
                "message": "Groq API test successful",
                "topics_count": sum(len(v) if isinstance(v, list) else 0 for v in topics.values()),
                "categories": list(topics.keys()) if topics else []
            }
        except Exception as e:
            logger.error(f"Groq API test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Groq API test failed - check logs for details"
            }

    def get_topic_details(self, topic: str, category: str) -> Dict[str, Any]:
        """
        Get detailed information about a trending topic using Groq API
        """
        if not self.groq_api_key:
            logger.error("Groq API key not configured")
            return {
                "success": False,
                "error": "Groq API key not configured"
            }
            
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare the prompt for Groq
            if topic == category:
                # This is a category-specific request
                prompt = f"""
                Provide detailed information about the category "{category}" in social media and digital marketing.
                Format the response as a JSON object with the following structure:
                {{
                    "overview": "A comprehensive overview of this category and its importance in digital marketing",
                    "keyPoints": ["Key point 1", "Key point 2", "Key point 3"],
                    "relatedTopics": ["Related topic 1", "Related topic 2", "Related topic 3"]
                }}
                Include specific campaign ideas and strategies for this category.
                Keep the response concise and focused on information that would be useful for social media content creation.
                """
            else:
                # Regular topic request
                prompt = f"""
                Provide detailed information about the trending topic "{topic}" in the category "{category}".
                Format the response as a JSON object with the following structure:
                {{
                    "overview": "A brief overview of the topic",
                    "keyPoints": ["Key point 1", "Key point 2", "Key point 3"],
                    "relatedTopics": ["Related topic 1", "Related topic 2", "Related topic 3"]
                }}
                Keep the response concise and focused on information that would be useful for social media content creation.
                """
            
            payload = {
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that provides information about trending topics and marketing categories for social media content creation."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.groq_api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Extract JSON from the response
                try:
                    # Find JSON in the response (it might be wrapped in markdown code blocks)
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        json_str = content.split("```")[1].strip()
                    else:
                        json_str = content.strip()
                        
                    details = json.loads(json_str)
                    
                    return {
                        "success": True,
                        "details": details
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Groq API response: {e}")
                    return {
                        "success": False,
                        "error": "Failed to parse API response",
                        "raw_response": content
                    }
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error fetching topic details: {str(e)}")
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

# Global service instance
trending_service = TrendingTopicsService()