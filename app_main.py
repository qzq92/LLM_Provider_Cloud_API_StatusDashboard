"""
LLM APIs & Cloud Services Status Dashboard
A Streamlit application for monitoring API and cloud service statuses.
"""
import asyncio
import pytz
import logging
import sys
import streamlit as st
from helpers import (
    get_openai_status, get_deepseek_status, get_gemini_status, get_anthropic_status,
    get_aws_status, get_gcp_status, get_azure_status, get_alicloud_status, get_perplexity_status, 
    get_langsmith_status, get_llamaindex_status, get_dify_status, cleanup_resources
)
from datetime import datetime

# Initialize session state for caching
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'cached_statuses' not in st.session_state:
    st.session_state.cached_statuses = None
if 'cache_timestamp' not in st.session_state:
    st.session_state.cache_timestamp = None

# Configure logging to appear in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # This ensures logs go to console
    ]
)

# Set up logger for this module
logger = logging.getLogger(__name__)

# Simple Streamlit dashboard - no complex shutdown handling needed

# Configure the page
st.set_page_config(
    page_title="LLM APIs & Cloud Services Status Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .status-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid;
        margin: 0.5rem 0;
    }
    .status-operational {
        border-left-color: #00ff00;
        background-color: #f0fff0;
    }
    .status-issues {
        border-left-color: #ff6b6b;
        background-color: #fff0f0;
    }
    .status-unknown {
        border-left-color: #ffa500;
        background-color: #fff8f0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .status-indicator {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .status-card p a {
        color: #007bff;
        text-decoration: none;
    }
    .status-card p a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

def create_status_card(service_data: dict, include_details=True) -> str:
    """Create a status card for a service."""
    if service_data["status"] == "Unknown":
        status_class = "status-unknown"
        # No operational key is available
        status_icon = "🟡"
        logger.warning("Service %s is unknown", service_data["name"])
    elif service_data["status"] == "Operational":
        status_icon = "🟢"
        status_class = "status-operational"
    else:
        status_icon = "🔴"
        status_class = "status-issues"
    # Get source URL. Default to # if not available
    status_url = service_data.get('status_url', '#')

    # Create basic card content
    card_content = f"""
    <div class="status-card {status_class}">
        <div class="status-indicator">{status_icon}<h3>{service_data['name']}</h3></div>
        <p><strong>Status:</strong> {service_data['status']}</p>
        <p><strong>Source:</strong> <a href='{status_url}' target='_blank'>{status_url}</a></p>
    """
    
    if status_class == "status-issues" and include_details:
        # Add issue link for disrupted services
        issue_link = service_data.get('issue_link')
        if issue_link and issue_link.startswith("http"):
            card_content += f"""<strong>More details:</strong> <a href='{issue_link}' target='_blank'>{issue_link}</a>"""
        else:
            card_content += f"""<strong>More details:</strong> {issue_link}"""

    card_content += "</div>"
    return card_content


def _run_async_status_checker(checker):
    """Run an async checker in an isolated event loop inside a worker thread."""
    return asyncio.run(checker())

async def fetch_all_statuses():
    """Fetch all statuses concurrently using asyncio.gather()."""
    logger.info("Fetching all service statuses concurrently with asyncio")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Update progress
    progress_bar.progress(0.1)
    status_text.text("🚀 Starting concurrent status checks...")
    
    try:
        # Run all status checks in worker threads to avoid blocking the event loop
        # (many helpers use blocking I/O like requests/feedparser/selenium).
        results = await asyncio.gather(
            asyncio.to_thread(_run_async_status_checker, get_openai_status),
            asyncio.to_thread(_run_async_status_checker, get_deepseek_status),
            asyncio.to_thread(get_gemini_status),  # Run sync function in thread
            asyncio.to_thread(_run_async_status_checker, get_anthropic_status),
            asyncio.to_thread(_run_async_status_checker, get_perplexity_status),
            asyncio.to_thread(_run_async_status_checker, get_langsmith_status),
            asyncio.to_thread(_run_async_status_checker, get_llamaindex_status),
            asyncio.to_thread(get_dify_status),  # Run sync function in thread
            asyncio.to_thread(_run_async_status_checker, get_aws_status),
            asyncio.to_thread(_run_async_status_checker, get_gcp_status),
            asyncio.to_thread(_run_async_status_checker, get_azure_status),
            asyncio.to_thread(get_alicloud_status),  # Run sync function in thread
            return_exceptions=True  # Don't fail if one service fails
        )
        
        # Update progress
        progress_bar.progress(0.8)
        status_text.text("✅ All status checks completed!")
        
        # Convert results to dictionary format
        service_names = [
            'openai', 'deepseek', 'gemini', 'anthropic', 'perplexity', 
            'langsmith', 'llamaindex', 'dify', 'aws', 'gcp', 'azure', 'alicloud'
        ]
        status_results = {}
        
        for _, (service_name, result) in enumerate(zip(service_names, results)):
            if isinstance(result, Exception):
                logger.error("Error fetching %s status: %s", service_name, result)
                status_results[service_name] = {
                    "name": f"{service_name.title()} Status",
                    "status": "Unknown",
                    "status_url": "#",
                    "last_update": "N/A",
                    "title": "Error",
                    "description": f"Error: {str(result)}"
                }
            else:
                # Convert datetime objects to strings for serialization
                serialized_result = {}
                for key, value in result.items():
                    if isinstance(value, datetime):
                        serialized_result[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        serialized_result[key] = value
                status_results[service_name] = serialized_result
        
        # Update progress
        progress_bar.progress(1.0)
        
        return status_results
        
    except Exception as e:
        logger.error("Error in fetch_all_statuses: %s", e)
        progress_bar.progress(1.0)
        status_text.text("❌ Error occurred during status checks")
        return {}

def main():
    """Main function to run the Streamlit dashboard."""
    logger.info("Starting Dashboard")
    
    st.title("📊 LLM APIs & Cloud Services Status Dashboard (refresh every 5 minutes)")
    # Client-side auto refresh every 5 minutes (non-blocking on server thread).
    st.markdown(
        "<meta http-equiv='refresh' content='300'>",
        unsafe_allow_html=True
    )

    # Get current time for display
    gmt_plus_8_timezone = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(tz=gmt_plus_8_timezone)
    last_updated = current_time.strftime('%d-%m-%Y %H:%M:%S')
    
    # Simple auto-refresh mechanism
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = current_time
    
    # Calculate time since last refresh
    time_since_refresh = (current_time - st.session_state.last_refresh_time).seconds
    
    # Display last refresh time
    st.info(f"⏰ **Last Refresh (GMT+8):** {last_updated}")
    
    # Auto-refresh logic - check if 300 seconds have passed
    if time_since_refresh >= 300:
        # Update the last refresh time
        st.session_state.last_refresh_time = current_time
        # Clear cache to force fresh data fetch
        st.session_state.cached_statuses = None
        st.session_state.cache_timestamp = None

    # Check if we need to fetch new data
    should_refresh = (
        st.session_state.cached_statuses is None or
        st.session_state.cache_timestamp is None
    )
    
    if should_refresh:
        # Fetch statuses with caching
        all_statuses = asyncio.run(fetch_all_statuses())
        st.session_state.cached_statuses = all_statuses
        st.session_state.cache_timestamp = current_time
        st.session_state.last_refresh = current_time
    else:
        # Use cached data
        all_statuses = st.session_state.cached_statuses
    openai_data = all_statuses['openai']
    deepseek_data = all_statuses['deepseek']
    gemini_data = all_statuses['gemini']
    anthropic_data = all_statuses['anthropic']
    perplexity_data = all_statuses['perplexity']
    langsmith_data = all_statuses['langsmith']
    llamaindex_data = all_statuses['llamaindex']
    dify_data = all_statuses['dify']
    aws_data = all_statuses['aws']
    gcp_data = all_statuses['gcp']
    azure_data = all_statuses['azure']
    alicloud_data = all_statuses['alicloud']
            

    # LLM API Status Section
    st.header("🤖 LLM API Status")
    st.markdown("Monitoring OpenAI, DeepSeek, Gemini, Perplexity and Anthropic API availability")

    # Create columns for LLM APIs
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(create_status_card(openai_data), unsafe_allow_html=True)

    with col2:
        st.markdown(create_status_card(deepseek_data), unsafe_allow_html=True)

    with col3:
        st.markdown(create_status_card(gemini_data), unsafe_allow_html=True)

    with col4:
        st.markdown(create_status_card(anthropic_data), unsafe_allow_html=True)

    with col5:
        st.markdown(create_status_card(perplexity_data), unsafe_allow_html=True)

    # LangSmith, LlamaIndex & Dify API Status Section
    st.header("🔧 Other LLM related platforms API status")
    st.markdown("Monitoring LangSmith, LlamaIndex and Dify API availability for LLM observability and tracing")

    # Create columns for LangSmith, LlamaIndex and Dify
    col_langsmith, col_llamaindex, col_dify = st.columns(3)
    
    with col_langsmith:
        st.markdown(create_status_card(langsmith_data), unsafe_allow_html=True)
    
    with col_llamaindex:
        st.markdown(create_status_card(llamaindex_data), unsafe_allow_html=True)
    
    with col_dify:
        st.markdown(create_status_card(dify_data), unsafe_allow_html=True)

    # Cloud Services Status Section
    st.header("☁️ Selected Cloud Services Status")
    st.markdown("Note: Due to large number of service offered, it is not possible to provide a link to actual cause. Please refer to respective status page for more details.")

    # Create columns for Cloud Services
    col6, col7, col8, col9 = st.columns(4)

    with col6:
        st.markdown(create_status_card(aws_data, include_details=False), unsafe_allow_html=True)

    with col7:
        st.markdown(create_status_card(gcp_data, include_details=False), unsafe_allow_html=True)

    with col8:
        st.markdown(create_status_card(azure_data, include_details=False), unsafe_allow_html=True)

    with col9:
        st.markdown(create_status_card(alicloud_data, include_details=False), unsafe_allow_html=True)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down gracefully...")
        cleanup_resources()
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        cleanup_resources()
        raise