"""
LLM & Cloud API Status Dashboard
A Streamlit application for monitoring API and cloud service statuses.
"""
import time
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

    return f"""
    <div class="status-card {status_class}">
        <div class="status-indicator">{status_icon}</div>
        <h3>{service_data['name']}</h3>
        <p><strong>Status:</strong> {service_data['status']}</p>
        <p><strong>Last Update:</strong> {service_data['last_update']}</p>
        <p><strong>Details:</strong> {service_data['description']}</p>
    </div>
    """

def main():
    """Main function to run the Streamlit dashboard."""
    st.title("📊 LLM & Cloud API Status Dashboard")
    st.markdown("Real-time monitoring of LLM APIs and Cloud Services")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30 seconds)", value=True)
    if auto_refresh:
        st.sidebar.info("Dashboard will refresh every 30 seconds")
        time.sleep(30)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()

    # Last updated timestamp
    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.sidebar.markdown(f"**Last Updated:** {last_updated}")

    # LLM API Status Section
    st.header("🤖 LLM API Status")
    st.markdown("Monitoring OpenAI, DeepSeek, Gemini, and Anthropic API availability")

    # Create columns for LLM APIs
    col1, col2, col3, col4 = st.columns(4)

    with st.spinner("Fetching LLM API statuses..."):
        # Fetch LLM API statuses
        openai_data = get_openai_status()
        deepseek_data = get_deepseek_status()
        gemini_data = get_gemini_status()
        anthropic_data = get_anthropic_status()

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

    with st.spinner("Fetching Cloud Services statuses..."):
        # Fetch Cloud Services statuses
        aws_data = get_aws_status()
        gcp_data = get_gcp_status()
        azure_data = get_azure_status()

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
    st.markdown("**Note:** This dashboard provides 30 seconds status monitoring. Data is refreshed automatically.")

    # Debug information (collapsible)
    with st.expander("🔧 Debug Information"):
        st.json({
            "LLM Services": llm_services,
            "Cloud Services": cloud_services,
            "Last Refresh": datetime.now().isoformat()
        })

if __name__ == "__main__":
    main()