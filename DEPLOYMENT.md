# Streamlit Community Cloud Deployment Guide

## Prerequisites

1. **GitHub Account**: You need a GitHub account
2. **GitHub Repository**: Your code must be in a public GitHub repository
3. **Streamlit Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository has the following structure:
```
your-repo/
├── app_main.py          # Main Streamlit app
├── helpers.py           # Helper functions
├── requirements.txt     # Python dependencies
├── .streamlit/
│   ├── config.toml      # Streamlit configuration
│   └── secrets.toml     # Local secrets (optional)
├── README.md
└── img/
    └── sample_dashboard.png
```

### 2. Update Requirements

Make sure your `requirements.txt` includes all necessary dependencies:
```
streamlit>=1.28.0
requests>=2.31.0
feedparser>=6.0.10
beautifulsoup4>=4.12.0
pytz>=2023.3
selenium>=4.15.0
undetected-chromedriver>=3.5.0
webdriver-manager>=4.0.0
```

### 3. Deploy to Streamlit Community Cloud

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Click "New app"**
3. **Fill in the details:**
   - **Repository**: `your-username/your-repo-name`
   - **Branch**: `main` (or your default branch)
   - **Main file path**: `app_main.py`
   - **App URL**: Choose a unique URL (e.g., `llm-status-dashboard`)

4. **Click "Deploy!"**

### 4. Configure Chrome for Cloud Deployment

Since your app uses Chrome for web scraping, you may need to configure Chrome options for the cloud environment:

```python
# In helpers.py, update Chrome options for cloud deployment
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-plugins")
chrome_options.add_argument("--disable-images")
chrome_options.add_argument("--disable-javascript")
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--disable-background-timer-throttling")
chrome_options.add_argument("--disable-backgrounding-occluded-windows")
chrome_options.add_argument("--disable-renderer-backgrounding")
```

### 5. Handle Chrome Dependencies

For Streamlit Community Cloud, you might need to:

1. **Use a different Chrome setup** or
2. **Fallback to requests-only** for some services
3. **Use cloud-based browser services**

### 6. Environment Variables (if needed)

If you need any environment variables, add them in the Streamlit Community Cloud dashboard:
- Go to your app's settings
- Add any required environment variables

### 7. Monitor Deployment

- Check the deployment logs for any errors
- Test all functionality after deployment
- Monitor resource usage

## Troubleshooting

### Common Issues:

1. **Chrome/WebDriver Issues**: 
   - Streamlit Community Cloud has limited Chrome support
   - Consider using alternative scraping methods
   - Use `requests` + `BeautifulSoup` where possible

2. **Memory Issues**:
   - Chrome drivers consume significant memory
   - Consider implementing driver cleanup
   - Use connection pooling

3. **Timeout Issues**:
   - Some services might timeout in cloud environment
   - Implement proper error handling
   - Add retry mechanisms

### Alternative Deployment Options:

If Streamlit Community Cloud doesn't work due to Chrome limitations:

1. **Heroku**: More control over environment
2. **Railway**: Good for Python apps
3. **Render**: Free tier available
4. **DigitalOcean App Platform**: More resources

## Post-Deployment

1. **Test all functionality**
2. **Monitor performance**
3. **Update documentation**
4. **Set up monitoring/alerts**
