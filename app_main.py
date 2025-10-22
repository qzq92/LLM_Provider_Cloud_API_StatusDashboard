"""
LLM & Cloud API Status Dashboard
A Streamlit application for monitoring API and cloud service statuses.
"""
import time
import asyncio
import concurrent.futures
import pytz
from datetime import datetime
import streamlit as st
from helpers import (
    get_openai_status, get_deepseek_status, get_gemini_status, get_anthropic_status,
    get_aws_status, get_gcp_status, get_azure_status
)

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
</style>
""", unsafe_allow_html=True)

def create_status_card(service_data):
    """Create a status card for a service."""
    status_class = "status-operational" if service_data["operational"] else "status-issues"
    if service_data["status"] == "Unknown":
        status_class = "status-unknown"

    status_icon = "🟢" if service_data["operational"] else "🔴"
    if service_data["status"] == "Unknown":
        status_icon = "🟡"

    # Create basic card content
    card_content = f"""
    <div class="status-card {status_class}">
        <div class="status-indicator">{status_icon}</div>
        <h3>{service_data['name']}</h3>
        <p><strong>Status:</strong> {service_data['status']}</p>
    """
    
    # For operational services, show minimal info (status + source)
    if service_data["operational"]:
        card_content += f"""
        <p><strong>Source:</strong> {service_data.get('title', 'API Status')}</p>
        """
    else:
        # For issues/unknown status, show full details
        card_content += f"""
        <p><strong>Last Update:</strong> {service_data['last_update']}</p>
        <p><strong>Details:</strong> {service_data['description']}</p>
        """
    
    card_content += "</div>"
    return card_content

@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_llm_statuses():
    """Fetch all LLM API statuses in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        openai_future = executor.submit(get_openai_status)
        deepseek_future = executor.submit(get_deepseek_status)
        gemini_future = executor.submit(get_gemini_status)
        anthropic_future = executor.submit(get_anthropic_status)
        
        # Wait for all to complete
        openai_data = openai_future.result()
        deepseek_data = deepseek_future.result()
        gemini_data = gemini_future.result()
        anthropic_data = anthropic_future.result()
        
        return openai_data, deepseek_data, gemini_data, anthropic_data

@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_cloud_statuses():
    """Fetch all cloud service statuses in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        aws_future = executor.submit(get_aws_status)
        gcp_future = executor.submit(get_gcp_status)
        azure_future = executor.submit(get_azure_status)
        
        # Wait for all to complete
        aws_data = aws_future.result()
        gcp_data = gcp_future.result()
        azure_data = azure_future.result()
        
        return aws_data, gcp_data, azure_data

def fetch_all_statuses():
    """Fetch all statuses in parallel with progress tracking."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize results
    results = {}
    
    # Create thread pool for all services
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        # Submit all tasks
        futures = {
            'openai': executor.submit(get_openai_status),
            'deepseek': executor.submit(get_deepseek_status),
            'gemini': executor.submit(get_gemini_status),
            'anthropic': executor.submit(get_anthropic_status),
            'aws': executor.submit(get_aws_status),
            'gcp': executor.submit(get_gcp_status),
            'azure': executor.submit(get_azure_status),
        }
        
        # Process results as they complete
        completed = 0
        total = len(futures)
        
        for service_name, future in futures.items():
            try:
                results[service_name] = future.result(timeout=10)  # 10 second timeout per service
                completed += 1
                progress = completed / total
                progress_bar.progress(progress)
                status_text.text(f"Fetched {service_name}... ({completed}/{total})")
            except Exception as e:
                st.error(f"Error fetching {service_name}: {e}")
                # Provide fallback data
                results[service_name] = {
                    "name": service_name.title(),
                    "status": "Error",
                    "operational": False,
                    "last_update": "N/A",
                    "title": "Error",
                    "description": f"Failed to fetch status: {str(e)}"
                }
                completed += 1
                progress = completed / total
                progress_bar.progress(progress)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    return results

def main():
    """Main function to run the Streamlit dashboard."""
    st.title("📊 LLM & Cloud API Status Dashboard")
    st.markdown("Near Real-time monitoring of LLM APIs and Cloud Services")

    # Sidebar controls
    st.sidebar.header("⚙️ Controls")
    
    # Loading strategy selection
    loading_strategy = st.sidebar.selectbox(
        "Loading Strategy",
        ["Parallel (Fast)", "Sequential (Reliable)"],
        index=0,
        help="Choose how to fetch API statuses"
    )
    
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30 seconds)", value=False)
    if auto_refresh:
        st.sidebar.info("Dashboard will refresh every 30 seconds")
        time.sleep(30)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()

    # Last updated timestamp in GMT+8
    # Define the GMT+8 timezone
    gmt_plus_8_timezone = pytz.timezone('Asia/Shanghai') # Or another city in GMT+8, e.g., 'Asia/Singapore'
    last_updated = datetime.now(tz=gmt_plus_8_timezone).strftime('%d-%m-%Y %H:%M:%S')

    st.sidebar.markdown(f"**Last Updated (GMT+8):** {last_updated}")

    # Fetch statuses based on selected strategy
    if loading_strategy == "Parallel (Fast)":
        # Use parallel loading with progress
        all_statuses = fetch_all_statuses()
        openai_data = all_statuses['openai']
        deepseek_data = all_statuses['deepseek']
        gemini_data = all_statuses['gemini']
        anthropic_data = all_statuses['anthropic']
        aws_data = all_statuses['aws']
        gcp_data = all_statuses['gcp']
        azure_data = all_statuses['azure']
    else:  # Sequential (Reliable)
        # Use original sequential loading
        with st.spinner("Fetching statuses sequentially..."):
            openai_data = get_openai_status()
            deepseek_data = get_deepseek_status()
            gemini_data = get_gemini_status()
            anthropic_data = get_anthropic_status()
            aws_data = get_aws_status()
            gcp_data = get_gcp_status()
            azure_data = get_azure_status()

    # LLM API Status Section
    st.header("🤖 LLM API Status")
    st.markdown("Monitoring OpenAI, DeepSeek, Gemini, and Anthropic API availability")

    # Create columns for LLM APIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(create_status_card(openai_data), unsafe_allow_html=True)

    with col2:
        st.markdown(create_status_card(deepseek_data), unsafe_allow_html=True)

    with col3:
        st.markdown(create_status_card(gemini_data), unsafe_allow_html=True)

    with col4:
        st.markdown(create_status_card(anthropic_data), unsafe_allow_html=True)

    # Cloud Services Status Section
    st.header("☁️ Cloud Services Status")
    st.markdown("Monitoring AWS, Google Cloud Platform, and Microsoft Azure")

    # Create columns for Cloud Services
    col5, col6, col7 = st.columns(3)

    with col5:
        st.markdown(create_status_card(aws_data), unsafe_allow_html=True)

    with col6:
        st.markdown(create_status_card(gcp_data), unsafe_allow_html=True)

    with col7:
        st.markdown(create_status_card(azure_data), unsafe_allow_html=True)

    # Summary metrics
    st.header("📈 Summary")

    # Calculate summary metrics
    llm_services = [openai_data, deepseek_data, gemini_data, anthropic_data]
    cloud_services = [aws_data, gcp_data, azure_data]

    llm_operational = sum(1 for service in llm_services if service["operational"])
    cloud_operational = sum(1 for service in cloud_services if service["operational"])

    col8, col9, col10 = st.columns(3)

    with col8:
        llm_percentage = llm_operational/len(llm_services)*100
        st.metric(
            label="LLM APIs Operational",
            value=f"{llm_operational}/{len(llm_services)}",
            delta=f"{llm_percentage:.1f}%"
        )

    with col9:
        cloud_percentage = cloud_operational/len(cloud_services)*100
        st.metric(
            label="Cloud Services Operational",
            value=f"{cloud_operational}/{len(cloud_services)}",
            delta=f"{cloud_percentage:.1f}%"
        )

    with col10:
        total_operational = llm_operational + cloud_operational
        total_services = len(llm_services) + len(cloud_services)
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
    with st.expander("📊 Performance Metrics"):
        col_perf1, col_perf2, col_perf3 = st.columns(3)
        
        with col_perf1:
            st.metric("Loading Strategy", loading_strategy)
        
        with col_perf2:
            st.metric("Cache Status", "Enabled" if loading_strategy == "Cached (Fastest)" else "Disabled")
        
        with col_perf3:
            st.metric("Parallel Workers", "7" if loading_strategy == "Parallel (Fast)" else "1")

    # Debug information (collapsible)
    with st.expander("🔧 Debug Information"):
        st.json({
            "LLM Services": llm_services,
            "Cloud Services": cloud_services,
            "Last Refresh": datetime.now().isoformat(),
            "Loading Strategy": loading_strategy
        })

if __name__ == "__main__":
    main()