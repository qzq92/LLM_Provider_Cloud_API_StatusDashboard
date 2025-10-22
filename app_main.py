"""
LLM & Cloud API Status Dashboard
A Streamlit application for monitoring API and cloud service statuses.
"""
import time
import concurrent.futures
import asyncio
import pytz
import logging
import sys
from datetime import datetime
import streamlit as st
from helpers import (
    get_openai_status, get_deepseek_status, get_gemini_status, get_anthropic_status,
    get_aws_status, get_gcp_status, get_azure_status, get_perplexity_status, get_langsmith_status
)

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

# Configure the page
st.set_page_config(
    page_title="LLM & Cloud API Status Dashboard",
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
        logger.warning(f"Service {service_data['name']} is unknown")
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


def run_gemini_status():
    """Wrapper function to run async Gemini status in thread pool."""
    return asyncio.run(get_gemini_status())

async def fetch_all_statuses():
    """Fetch all statuses concurrently using asyncio.gather()."""
    logger.info("Fetching all service statuses concurrently with asyncio")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Update progress
    progress_bar.progress(0.1)
    status_text.text("🚀 Starting concurrent status checks...")
    
    try:
        # Use asyncio.gather() to run all status functions concurrently
        results = await asyncio.gather(
            get_openai_status(),
            get_deepseek_status(), 
            get_gemini_status(),
            get_anthropic_status(),
            get_perplexity_status(),
            get_langsmith_status(),
            get_aws_status(),
            get_gcp_status(),
            get_azure_status(),
            return_exceptions=True  # Don't fail if one service fails
        )
        
        # Update progress
        progress_bar.progress(0.8)
        status_text.text("✅ All status checks completed!")
        
        # Convert results to dictionary format
        service_names = ['openai', 'deepseek', 'gemini', 'anthropic', 'perplexity', 'langsmith', 'aws', 'gcp', 'azure']
        status_results = {}
        
        for i, (service_name, result) in enumerate(zip(service_names, results)):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {service_name} status: {result}")
                status_results[service_name] = {
                    "name": f"{service_name.title()} Status",
                    "status": "Unknown",
                    "status_url": "#",
                    "last_update": "N/A",
                    "title": "Error",
                    "description": f"Error: {str(result)}"
                }
            else:
                status_results[service_name] = result
        
        # Update progress
        progress_bar.progress(1.0)
        status_text.text("🎉 Status dashboard ready!")
        
        return status_results
        
    except Exception as e:
        logger.error(f"Error in fetch_all_statuses: {e}")
        progress_bar.progress(1.0)
        status_text.text("❌ Error occurred during status checks")
        return {}

def main():
    """Main function to run the Streamlit dashboard."""
    logger.info("Starting LLM & Cloud API Status Dashboard")
    st.title("📊 LLM & Cloud API Status Dashboard")
    st.markdown("LLM APIs and Cloud Services Status")
    
    # Auto-refresh functionality
    st.markdown("🔄 **Auto-refresh every 30 seconds**")
    
    # Get current time for display
    gmt_plus_8_timezone = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(tz=gmt_plus_8_timezone)
    last_updated = current_time.strftime('%d-%m-%Y %H:%M:%S')
    
    # Display last refresh time and controls on main screen
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"⏰ **Last Refresh (GMT+8):** {last_updated}")
    
    with col2:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    
    with col3:
        countdown_placeholder = st.empty()
        countdown_placeholder.info("⏳ Next refresh in 30 seconds...")

    # Fetch statuses based on selected strategy

    # Use parallel loading with progress
    all_statuses = asyncio.run(fetch_all_statuses())
    openai_data = all_statuses['openai']
    deepseek_data = all_statuses['deepseek']
    gemini_data = all_statuses['gemini']
    anthropic_data = all_statuses['anthropic']
    perplexity_data = all_statuses['perplexity']
    langsmith_data = all_statuses['langsmith']
    aws_data = all_statuses['aws']
    gcp_data = all_statuses['gcp']
    azure_data = all_statuses['azure']
            

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

    # LangSmith API Status Section
    st.header("🔧 LangSmith API Status")
    st.markdown("Monitoring LangSmith API availability for LLM observability and tracing")

    # Create column for LangSmith
    col_langsmith = st.columns(1)[0]
    with col_langsmith:
        st.markdown(create_status_card(langsmith_data), unsafe_allow_html=True)

    # Cloud Services Status Section
    st.header("☁️ Selected Cloud Services Status")
    st.markdown("Note: Due to large number of service offered, it is not possible to provide a link to actual cause. Please refer to respsective status page for more details.")

    # Create columns for Cloud Services
    col6, col7, col8 = st.columns(3)

    with col6:
        st.markdown(create_status_card(aws_data, include_details=False), unsafe_allow_html=True)

    with col7:
        st.markdown(create_status_card(gcp_data, include_details=False), unsafe_allow_html=True)

    with col8:
        st.markdown(create_status_card(azure_data, include_details=False), unsafe_allow_html=True)

    # Summary metrics
    st.header("📈 Summary")

    # Calculate summary metrics
    llm_services = [openai_data, deepseek_data, gemini_data, anthropic_data, perplexity_data]
    langsmith_services = [langsmith_data]
    cloud_services = [aws_data, gcp_data, azure_data]

    llm_operational = sum(1 for service in llm_services if service["status"] == "Operational")
    langsmith_operational = sum(1 for service in langsmith_services if service["status"] == "Operational")
    cloud_operational = sum(1 for service in cloud_services if service["status"] == "Operational")

    col9, col10, col11, col12 = st.columns(4)

    with col9:
        llm_percentage = llm_operational/len(llm_services)*100
        st.metric(
            label="LLM APIs Operational",
            value=f"{llm_operational}/{len(llm_services)}",
            delta=f"{llm_percentage:.1f}%"
        )

    with col10:
        langsmith_percentage = langsmith_operational/len(langsmith_services)*100
        st.metric(
            label="LangSmith API Operational",
            value=f"{langsmith_operational}/{len(langsmith_services)}",
            delta=f"{langsmith_percentage:.1f}%"
        )

    with col11:
        cloud_percentage = cloud_operational/len(cloud_services)*100
        st.metric(
            label="Cloud Services Operational",
            value=f"{cloud_operational}/{len(cloud_services)}",
            delta=f"{cloud_percentage:.1f}%"
        )

    with col12:
        total_operational = llm_operational + langsmith_operational + cloud_operational
        total_services = len(llm_services) + len(langsmith_services) + len(cloud_services)
        overall_percentage = total_operational/total_services*100
        st.metric(
            label="Overall Uptime",
            value=f"{total_operational}/{total_services}",
            delta=f"{overall_percentage:.1f}%"
        )
    
    # Footer
    st.markdown("---")
    st.markdown("**Note:** This dashboard provides near real-time status monitoring. Operational services show minimal information, while issues display full details.")

    # Performance metrics
    # with st.expander("📊 Performance Metrics"):
    #     col_perf1, col_perf2, col_perf3 = st.columns(3)
        
    #     with col_perf1:
    #         st.metric("Loading Strategy", "Parallel")
        
    #     with col_perf2:
    #         st.metric("Cache Status", "Enabled")
        
    #     with col_perf3:
    #         st.metric("Parallel Workers", "9")

    # # Debug information (collapsible)
    # with st.expander("🔧 Debug Information"):
    #     st.json({
    #         "LLM Services": llm_services,
    #         "LangSmith Services": langsmith_services,
    #         "Cloud Services": cloud_services,
    #         "Last Refresh in GMT+8": datetime.now(tz=gmt_plus_8_timezone).strftime('%d-%m-%Y %H:%M:%S')
    #     })
    
    # Add JavaScript countdown timer for main screen
    st.markdown("""
    <script>
    function startCountdown() {
        let timeLeft = 30;
        // Target the countdown element in the main content area
        const countdownElement = document.querySelector('.stAlert .stMarkdown p');
        
        const timer = setInterval(() => {
            timeLeft--;
            if (countdownElement && countdownElement.textContent.includes('Next refresh')) {
                countdownElement.textContent = `⏳ Next refresh in ${timeLeft} seconds...`;
            }
            if (timeLeft <= 0) {
                clearInterval(timer);
            }
        }, 1000);
    }
    
    // Start countdown when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startCountdown);
    } else {
        startCountdown();
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Auto-refresh every 30 seconds
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()