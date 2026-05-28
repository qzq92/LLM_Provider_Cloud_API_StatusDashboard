"""
Helper functions for fetching API and cloud service statuses.
"""
import time
import feedparser
import threading
import logging
import requests
from typing import Dict, Any
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from browser_checks import (
    get_dify_status as browser_get_dify_status,
    get_gemini_status as browser_get_gemini_status,
    get_alicloud_status as browser_get_alicloud_status,
    cleanup_browser_resources,
)
from status_payloads import (
    build_operational_payload,
    build_unknown_payload,
    build_status_payload,
)
# Configure logging for helpers module
logger = logging.getLogger(__name__)

# Global session for HTTP requests to avoid connection pool issues
_http_session = None
_request_semaphore = threading.Semaphore(3)
_request_lock = threading.Lock()
DEFAULT_HTTP_TIMEOUT = 10

def get_http_session():
    """Get or create a global HTTP session with proper connection pooling."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        
        # Configure retry strategy with reduced attempts
        retry_strategy = Retry(
            total=2,              # Reduced: Only 2 retry attempts
            backoff_factor=0.5,   # Reduced: Shorter backoff time
            status_forcelist=[500, 502, 503, 504],  # Removed 429 to avoid rate limiting
        )
        
        # Configure adapter with retry strategy and reduced connection pool
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=2,   # Reduced: Number of connection pools
            pool_maxsize=5,       # Reduced: Maximum number of connections in pool
            pool_block=False      # Don't block when pool is full
        )
        
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
        
        # Add connection limits to prevent resource exhaustion
        _http_session.headers.update({
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=5, max=10',
            'User-Agent': 'LLM-Status-Dashboard/1.0'
        })
        
        logger.info("Created new HTTP session with optimized connection pooling")
    
    return _http_session


def fetch_remote_content(url: str) -> bytes:
    """Fetch remote content with shared session and bounded concurrency."""
    with _request_semaphore:
        session = get_http_session()
        response = session.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
        response.raise_for_status()
        return response.content


def cleanup_resources():
    """Clean up global resources to prevent connection pool issues."""
    global _http_session
    cleanup_browser_resources()
    
    # Clean up HTTP session with aggressive connection cleanup
    if _http_session is not None:
        try:
            # Close all connections in the pool
            _http_session.close()
            # Force garbage collection of connections
            import gc
            gc.collect()
            logger.info("Cleaned up HTTP session and connections")
        except Exception as e:
            logger.warning("Error cleaning up HTTP session: %s", e)
        finally:
            _http_session = None


# API statuses
async def get_openai_status() -> Dict[str, Any]:
    """
    Get OpenAI API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from OpenAI's RSS feed
    - Checks if the description contains "all impacted services have now fully recovered"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "OpenAI API Status"
    try:
        rss_url = 'https://status.openai.com/feed.rss'
        status_url = 'https://status.openai.com'
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            latest_entry = feed.entries[0]
            issue_link = latest_entry.link
            description = latest_entry.description
            # Check for operational issues
            description_lower = description.lower()

            is_operational = "all impacted services have now fully recovered" in description_lower
            
            return build_operational_payload(name, is_operational, status_url, issue_link)
    except Exception as e:
        logger.error(f"Error fetching OpenAI status: {e}")
    
    return build_unknown_payload(name, status_url)

async def get_deepseek_status() -> Dict[str, Any]:
    """
    Get DeepSeek API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from DeepSeek's Atom feed
    - Checks if the latest feed content contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If feed parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Deepseek API Status"
    try:
        rss_url = 'https://status.deepseek.com/history.atom'
        status_url = 'https://status.deepseek.com'
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            latest_entry = feed.entries[0]
            issue_link = latest_entry.link
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            
            # Check for operational issues
            content_lower = content.lower()

            # Look for specific keywords in the content
            is_operational = True if "resolved" in content_lower else False
            
            return build_operational_payload(name, is_operational, status_url, issue_link)
    except Exception as e:
        logger.error(f"Error fetching DeepSeek status: {e}")
    
    return build_unknown_payload(name, status_url)

async def get_langsmith_status() -> Dict[str, Any]:
    """
    Get LangSmith API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from LangSmith's RSS feed
    - Checks if the description contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Langsmith US"
    try:
        rss_url = 'https://status.smith.langchain.com/feed.rss'
        status_url = 'https://status.smith.langchain.com'
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            latest_entry = feed.entries[0]
            issue_link = latest_entry.link
            description = latest_entry.description

            # Check for operational issues
            description_lower = description.lower()
            # Set to false if any of the keyword exist in description
            is_operational = "resolved" in description_lower or "complete" in description_lower
            return build_operational_payload(name, is_operational, status_url, issue_link)
    except Exception as e:
        logging.error("Error fetching LangSmith status: %s", e)
    
    return build_unknown_payload(name, status_url)


async def get_llamaindex_status() -> Dict[str, Any]:
    """
    Get LlamaIndex status from their status page.
    
    Operational Status Logic:
    - Fetches the LlamaIndex status page HTML content
    - Searches for <p class="color-secondary"> elements
    - Checks if any element contains "no incidents reported today"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If page parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "LlamaIndex"
    status_url = 'https://llamaindex.statuspage.io/'

    try:
        soup = BeautifulSoup(fetch_remote_content(status_url), 'html.parser')
        
        # Look for the nested <p class="color-secondary"> element
        color_secondary_elements = soup.find_all('p', class_='color-secondary')
        
        is_operational = False
        for element in color_secondary_elements:
            text_content = element.get_text().strip().lower()
            key_phrase = "no incidents reported today"
            if key_phrase in text_content:
                logger.info(f"LlamaIndex: Found required key phrase: {key_phrase} to indicate no issue")
                is_operational = True
                break
        
        return build_operational_payload(name, is_operational, status_url)

    except Exception as e:
        logging.error("Error fetching LlamaIndex status: %s", e)
    
    return build_unknown_payload(name, status_url)


# Dify status
def get_dify_status() -> Dict[str, Any]:
    return browser_get_dify_status()

def get_gemini_status() -> Dict[str, Any]:
    return browser_get_gemini_status()

# Add get perplexity status
async def get_perplexity_status() -> Dict[str, Any]:
    """
    Get Perplexity API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from Perplexity's RSS feed
    - Checks if the description contains "resolved" AND does not contain "api outage"
    - If both conditions met: Status = "Operational"
    - If not: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"

    Returns:
        Dict containing status information
    """
    name = "Perplexity API Status"
    try:
        rss_url = 'https://status.perplexity.com/history.rss'
        status_url = 'https://status.perplexity.com'
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            latest_entry = feed.entries[0]
            issue_link = latest_entry.link
            description = latest_entry.description
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower and not "api outage" in description_lower
            
            return build_operational_payload(name, is_operational, status_url, issue_link)
    except Exception as e:
        logger.error(f"Error fetching Perplexity status: {e}")
    
    return build_unknown_payload(name, status_url)

async def get_anthropic_status() -> Dict[str, Any]:
    """
    Get Anthropic API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from Anthropic's RSS feed
    - Checks if the description contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Anthropic API Status"
    try:
        rss_url = 'https://status.anthropic.com/history.rss'
        status_url = 'https://status.anthropic.com'
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            latest_entry = feed.entries[0]
            issue_link = latest_entry.link
            description = latest_entry.description
            description_lower = description.lower()
            is_operational = "resolved" in description_lower
            
            return build_operational_payload(name, is_operational, status_url, issue_link)
    except Exception as e:
        logger.error(f"Error fetching Anthropic status: {e}")
    
    return build_unknown_payload(name, status_url)

# Cloud related status using single RSS source
async def get_gcp_status() -> Dict[str, Any]:
    """
    Get Google Cloud Platform status (Global).
    
    Operational Status Logic:
    - Fetches the latest entry from GCP's Atom feed
    - Checks if the title contains "resolved:"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If feed parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Google Cloud Platform Status (Global)"
    try:
        # GCP Status API endpoint
        rss_url = 'https://status.cloud.google.com/en/feed.atom'
        status_url = 'https://status.cloud.google.com'
        logger.info(f"Parsing GCP status feed as feedparser object from {rss_url}")
        feed = feedparser.parse(fetch_remote_content(rss_url))
        
        if feed.entries:
            logger.info("Found feed in GCP, if latest feed shows resolved, means there are no issues")
            latest_entry = feed.entries[0]
            title = latest_entry.title
            # Check for operational issues based on title name
            title_lower = title.lower()
            is_operational = "resolved:" in title_lower
            
            return build_operational_payload(name, is_operational, status_url)
    except Exception as e:
        logger.error(f"Error fetching GCP status: {e}")
    
    return build_unknown_payload(name, status_url)

async def get_azure_status() -> Dict[str, Any]:
    """
    Get Microsoft Azure status (US).
    
    Operational Status Logic:
    - Fetches entries from Azure's RSS feed
    - If feed entries exist: Status = "Disrupted" (indicates ongoing issues)
    - If no feed entries: Status = "Operational" (no incidents reported)
    - If feed parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Microsoft Azure Status US"
    try:
        # Azure Status API endpoint
        rss_url = 'https://rssfeed.azure.status.microsoft/en-us/status/feed/'
        status_url = 'https://status.azure.com'
        logger.info("Parsing Azure status feed as feedparser object")
        feed = feedparser.parse(fetch_remote_content(rss_url))
        if feed.entries:
            logger.info("Found feed in Azure, indicates ongoing issues")
    
            return build_status_payload(name, "Disrupted", status_url)
        # No feed found, assume operational
        else:
            logger.info("Azure: No feed found, indicates normal status")
            return build_status_payload(name, "Operational", status_url)
    except Exception as e:
        logger.error(f"Error fetching Azure status: {e}")

    return build_unknown_payload(name, status_url)

async def get_aws_status() -> Dict[str, Any]:
    """
    Get AWS service status from AWS Global Health Dashboard.
    
    Operational Status Logic:
    - Fetches entries from AWS's RSS feed
    - If feed entries exist: Status = "Disrupted" (indicates ongoing issues)
    - If no feed entries: Status = "Operational" (no incidents reported)
    - If feed parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Amazon Web Service (AWS) Global Cloud Status"
    try:
        # AWS Health Dashboard endpoint
        rss_url = 'https://status.aws.amazon.com/rss/all.rss'
        status_url = 'https://health.aws.amazon.com/health/status'
        logger.info("Parsing AWS status feed as feedparser object")
        feed = feedparser.parse(fetch_remote_content(rss_url))
        if feed.entries:
            logger.info("Found feed in AWS, indicates ongoing issues")

            return build_status_payload(name, "Disrupted", status_url)
        # No feed found, assume operational
        else:
            logger.info("AWS: No feed found, indicates normal status")
            return build_status_payload(name, "Operational", status_url)

    except Exception as e:
        logger.error(f"Error fetching AWS status: {e}")
    
    return build_unknown_payload(name, status_url)


def get_alicloud_status() -> Dict[str, Any]:
    return browser_get_alicloud_status()