# app.py - Public Health Job Scraper
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import json
import re

# Try to import BeautifulSoup, with fallback
try:
    from bs4 import BeautifulSoup
    BEAUTIFUL_SOUP_AVAILABLE = True
except ImportError:
    BEAUTIFUL_SOUP_AVAILABLE = False

class SimpleJobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_recent_job(self, date_text):
        """Check if job was posted in last 24 hours"""
        if not date_text:
            return False
            
        date_text_lower = str(date_text).lower()
        recent_indicators = [
            'hours ago', 'hour ago', 'today', 'just now',
            '1 day ago', 'yesterday'
        ]
        
        return any(indicator in date_text_lower for indicator in recent_indicators)
    
    def scrape_reliefweb_api(self, search_term, max_jobs=20):
        """Scrape ReliefWeb using their official API"""
        st.info(f"🔍 Searching ReliefWeb for: {search_term}")
        
        url = "https://api.reliefweb.int/v1/jobs"
        params = {
            'appname': 'publichealth',
            'query[value]': search_term,
            'limit': max_jobs,
            'preset': 'latest'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for item in data.get('data', [])[:max_jobs]:
                try:
                    fields = item.get('fields', {})
                    
                    # Get organization name
                    org_name = "Unknown Organization"
                    if fields.get('source'):
                        org_name = fields['source'][0].get('name', org_name)
                    
                    # Get location
                    locations = []
                    if fields.get('country'):
                        locations = [loc.get('name', '') for loc in fields['country']]
                    location = ', '.join(locations) or 'Multiple Locations'
                    
                    job_data = {
                        'title': fields.get('title', 'No title'),
                        'organization': org_name,
                        'location': location,
                        'url': f"https://reliefweb.int/job/{item['id']}",
                        'date_posted': fields.get('date', {}).get('created', 'Unknown'),
                        'source': 'reliefweb',
                        'scraped_at': datetime.now().isoformat(),
                        'search_term': search_term
                    }
                    
                    job_data['is_recent'] = self.is_recent_job(job_data.get('date_posted', ''))
                    jobs.append(job_data)
                    
                except Exception as e:
                    continue
            
            return jobs
            
        except Exception as e:
            st.warning(f"ReliefWeb API failed, using mock data for demonstration")
            return self.get_mock_jobs(search_term)
    
    def get_mock_jobs(self, search_term):
        """Return mock job data for demonstration"""
        mock_jobs = [
            {
                'title': f'Public Health M&E Officer - {search_term.title()}',
                'organization': 'World Health Organization',
                'location': 'Geneva, Switzerland',
                'url': 'https://reliefweb.int/job/example1',
                'date_posted': '2 hours ago',
                'source': 'reliefweb',
                'scraped_at': datetime.now().isoformat(),
                'search_term': search_term,
                'is_recent': True
            },
            {
                'title': f'Monitoring & Evaluation Specialist - {search_term.title()}',
                'organization': 'UNICEF',
                'location': 'Multiple Locations',
                'url': 'https://reliefweb.int/job/example2',
                'date_posted': '1 day ago',
                'source': 'reliefweb',
                'scraped_at': datetime.now().isoformat(),
                'search_term': search_term,
                'is_recent': True
            },
            {
                'title': f'Health Data Analyst - {search_term.title()}',
                'organization': 'International Rescue Committee',
                'location': 'New York, USA',
                'url': 'https://reliefweb.int/job/example3',
                'date_posted': '3 days ago',
                'source': 'reliefweb',
                'scraped_at': datetime.now().isoformat(),
                'search_term': search_term,
                'is_recent': False
            }
        ]
        return mock_jobs
    
    def scrape_development_sites(self, search_term, sites=None):
        """Scrape multiple development job sites"""
        if sites is None:
            sites = ['reliefweb']
        
        all_jobs = []
        
        for site in sites:
            try:
                if site == 'reliefweb':
                    jobs = self.scrape_reliefweb_api(search_term)
                else:
                    continue
                
                all_jobs.extend(jobs)
                time.sleep(1)  # Be respectful
                
            except Exception as e:
                st.error(f"Failed to scrape {site}: {str(e)}")
                continue
        
        return all_jobs
    
    def filter_public_health_jobs(self, jobs):
        """Filter jobs for public health M&E relevance"""
        public_health_keywords = [
            'public health', 'monitoring', 'evaluation', 'm&e', 'data',
            'health', 'strategic information', 'commcare', 'dhis2',
            'survey', 'research', 'impact assessment', 'health program',
            'global health', 'health systems', 'epidemiology', 'health',
            'maternal', 'child health', 'hiv', 'tb', 'malaria', 'nutrition'
        ]
        
        filtered_jobs = []
        
        for job in jobs:
            job_text = f"{job['title']} {job.get('organization', '')}".lower()
            
            # Check if job matches public health criteria
            matches = sum(1 for keyword in public_health_keywords if keyword in job_text)
            relevance_score = matches / len(public_health_keywords)
            
            if relevance_score >= 0.2:  # At least 20% match
                job['relevance_score'] = round(relevance_score, 2)
                job['is_public_health'] = True
                filtered_jobs.append(job)
            else:
                job['relevance_score'] = round(relevance_score, 2)
                job['is_public_health'] = False
        
        return filtered_jobs

def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Public Health M&E Job Scraper",
        page_icon="🔍",
        layout="wide"
    )
    
    # Header
    st.title("🔍 Public Health M&E Job Scraper")
    st.markdown("Find public health monitoring and evaluation jobs from development organizations.")
    
    if not BEAUTIFUL_SOUP_AVAILABLE:
        st.info("💡 Using ReliefWeb API for job search (no BeautifulSoup required)")
    
    # Sidebar configuration
    st.sidebar.header("🔧 Configuration")
    
    # Search terms
    st.sidebar.subheader("Search Terms")
    default_terms = [
        "monitoring and evaluation",
        "M&E officer", 
        "public health",
        "health data"
    ]
    
    search_terms = []
    for i, term in enumerate(default_terms):
        if st.sidebar.checkbox(term, value=True, key=f"term_{i}"):
            search_terms.append(term)
    
    # Additional custom search term
    custom_term = st.sidebar.text_input("Add custom search term:")
    if custom_term and custom_term not in search_terms:
        search_terms.append(custom_term)
    
    # Target sites
    st.sidebar.subheader("Target Sites")
    sites = []
    if st.sidebar.checkbox("ReliefWeb", value=True):
        sites.append('reliefweb')
    
    # Job limits
    st.sidebar.subheader("Scraping Limits")
    max_jobs_per_search = st.sidebar.slider(
        "Max jobs per search term", 
        min_value=5, 
        max_value=30, 
        value=15
    )
    
    # Recent jobs filter
    show_only_recent = st.sidebar.checkbox("Show only recent jobs (last 24h)", value=False)
    
    # Scraping control
    st.sidebar.subheader("Scraping Control")
    run_scraper = st.sidebar.button("🚀 Start Job Search", type="primary")
    
    # Main content
    if run_scraper:
        if not search_terms:
            st.error("Please select at least one search term.")
            return
        
        if not sites:
            st.error("Please select at least one website to scrape.")
            return
        
        # Initialize scraper
        scraper = SimpleJobScraper()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_jobs = []
        total_searches = len(search_terms)
        
        for i, search_term in enumerate(search_terms):
            status_text.text(f"🔍 Searching for: '{search_term}'...")
            
            try:
                jobs = scraper.scrape_development_sites(search_term, sites)
                filtered_jobs = scraper.filter_public_health_jobs(jobs)
                all_jobs.extend(filtered_jobs)
                
                status_text.text(f"✅ Found {len(filtered_jobs)} jobs for '{search_term}'")
                
            except Exception as e:
                st.error(f"Error searching for '{search_term}': {str(e)}")
                continue
            
            finally:
                progress = (i + 1) / total_searches
                progress_bar.progress(progress)
                time.sleep(1)
        
        # Remove duplicates
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        progress_bar.progress(1.0)
        status_text.text(f"🎉 Search complete! Found {len(unique_jobs)} unique jobs.")
        
        # Display results
        display_results(unique_jobs, show_only_recent)

def display_results(jobs, show_only_recent):
    """Display results in Streamlit"""
    if not jobs:
        st.warning("No jobs found matching your criteria. Try adjusting your search terms.")
        return
    
    # Filter jobs if only recent requested
    if show_only_recent:
        jobs = [job for job in jobs if job.get('is_recent', False)]
        if not jobs:
            st.warning("No recent jobs found in the last 24 hours.")
            return
    
    # Create dataframe
    df = pd.DataFrame(jobs)
    
    # Display summary
    recent_count = sum(1 for job in jobs if job.get('is_recent', False))
    high_match_count = sum(1 for job in jobs if job.get('relevance_score', 0) > 0.7)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", len(jobs))
    with col2:
        st.metric("Recent Jobs", recent_count)
    with col3:
        st.metric("High Matches", high_match_count)
    with col4:
        sources = set(df['source'].tolist()) if not df.empty else set()
        st.metric("Sources", ", ".join(sources))
    
    if df.empty:
        return
        
    # Display jobs in a table
    st.subheader("📋 Job Results")
    
    # Create display dataframe with clickable links
    display_df = df.copy()
    display_df['Job Title'] = display_df.apply(
        lambda x: f'<a href="{x["url"]}" target="_blank" style="text-decoration:none; color:#0066cc; font-weight:bold;">{x["title"]}</a>', 
        axis=1
    )
    
    # Select and format columns
    display_df = display_df[['Job Title', 'organization', 'location', 'date_posted', 'source', 'relevance_score']]
    display_df.columns = ['Job Title', 'Organization', 'Location', 'Date Posted', 'Source', 'Relevance Score']
    
    # Format relevance score as percentage
    display_df['Relevance Score'] = display_df['Relevance Score'].apply(lambda x: f"{x*100:.0f}%")
    
    # Display the dataframe
    st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Download options
    st.subheader("📥 Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV download
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"public_health_jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # JSON download
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"public_health_jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    # Show recent jobs separately if not already filtered
    if not show_only_recent:
        recent_jobs = [job for job in jobs if job.get('is_recent', False)]
        if recent_jobs:
            st.subheader("🆕 Recent Jobs (Last 24 Hours)")
            for job in recent_jobs:
                with st.container():
                    st.markdown(f"### [{job['title']}]({job['url']})")
                    st.markdown(f"**{job['organization']}** • {job['location']} • {job['date_posted']}")
                    st.markdown("---")

if __name__ == "__main__":
    main()
