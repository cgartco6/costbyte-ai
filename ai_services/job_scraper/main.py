"""
Main job scraper service
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobScraper:
    """Main job scraping orchestrator"""
    
    def __init__(self):
        self.scrapers = {
            'careers24': Careers24Scraper(),
            'pnet': PNetScraper(),
            'indeed': IndeedScraper(),
            'linkedin': LinkedInScraper(),
            'careerjunction': CareerJunctionScraper(),
        }
        
        self.user_preferences_cache = {}
        self.job_cache = {}
        self.cache_expiry = timedelta(hours=1)
    
    async def scrape_for_user(self, user_id: str, preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape jobs for specific user"""
        
        logger.info(f"Scraping jobs for user {user_id}")
        
        all_jobs = []
        
        # Check cache first
        cache_key = f"user_{user_id}_{datetime.now().strftime('%Y%m%d%H')}"
        cached_jobs = self.job_cache.get(cache_key)
        
        if cached_jobs and datetime.now() - cached_jobs.get('timestamp', datetime.min) < self.cache_expiry:
            logger.info(f"Using cached jobs for user {user_id}")
            return cached_jobs['jobs']
        
        # Scrape from all sources
        scrape_tasks = []
        for scraper_name, scraper in self.scrapers.items():
            task = self.scrape_source(scraper, preferences)
            scrape_tasks.append(task)
        
        # Run all scrapers concurrently
        results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraping error: {result}")
                continue
            
            if result:
                all_jobs.extend(result)
        
        # Remove duplicates
        all_jobs = self.remove_duplicates(all_jobs)
        
        # Match jobs to user preferences
        matched_jobs = self.match_jobs_to_user(all_jobs, preferences)
        
        # Cache results
        self.job_cache[cache_key] = {
            'jobs': matched_jobs,
            'timestamp': datetime.now(),
            'count': len(matched_jobs)
        }
        
        logger.info(f"Found {len(matched_jobs)} matched jobs for user {user_id}")
        return matched_jobs
    
    async def scrape_source(self, scraper, preferences):
        """Scrape from a single source"""
        try:
            jobs = await scraper.scrape(preferences)
            return jobs
        except Exception as e:
            logger.error(f"Error scraping {scraper.__class__.__name__}: {e}")
            return []
    
    def remove_duplicates(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate job postings"""
        
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create unique identifier
            job_id = f"{job.get('source')}_{job.get('job_id')}_{job.get('title')}_{job.get('company')}"
            
            if job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def match_jobs_to_user(self, jobs: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match jobs to user preferences using AI"""
        
        from .job_matcher import JobMatcher
        
        matcher = JobMatcher()
        matched_jobs = []
        
        for job in jobs:
            match_score = matcher.calculate_match_score(job, preferences)
            
            if match_score >= preferences.get('min_match_score', 70):
                job['match_score'] = match_score
                job['match_reasons'] = matcher.get_match_reasons(job, preferences)
                matched_jobs.append(job)
        
        # Sort by match score
        matched_jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return matched_jobs
    
    def schedule_scraping(self):
        """Schedule scraping tasks"""
        
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # Schedule twice daily scraping (9 AM and 3 PM)
        scheduler.add_job(
            self.run_daily_scraping,
            'cron',
            hour='9,15',
            minute='0',
            id='daily_job_scraping'
        )
        
        # Schedule immediate scraping for new users
        scheduler.add_job(
            self.scrape_for_new_users,
            'interval',
            minutes=30,
            id='new_user_scraping'
        )
        
        scheduler.start()
    
    async def run_daily_scraping(self):
        """Run scraping for all active users"""
        
        from backend.apps.users.models import User
        
        active_users = User.objects.filter(
            has_paid=True,
            is_verified=True,
            is_active=True
        )
        
        logger.info(f"Running daily scraping for {active_users.count()} users")
        
        for user in active_users:
            try:
                preferences = self.get_user_preferences(user)
                jobs = await self.scrape_for_user(str(user.id), preferences)
                
                # Store jobs for user
                await self.store_jobs_for_user(user, jobs)
                
                # Notify user if new high-matching jobs found
                await self.notify_user_of_new_jobs(user, jobs)
                
            except Exception as e:
                logger.error(f"Error processing user {user.id}: {e}")
    
    def get_user_preferences(self, user):
        """Get user job search preferences"""
        
        cache_key = f"prefs_{user.id}"
        if cache_key in self.user_preferences_cache:
            return self.user_preferences_cache[cache_key]
        
        preferences = {
            'keywords': user.profile.skills if hasattr(user, 'profile') else [],
            'locations': user.preferred_locations,
            'industries': user.preferred_industries,
            'salary_min': float(user.salary_expectation or 0),
            'job_types': user.profile.job_types if hasattr(user, 'profile') else ['full-time'],
            'experience_level': user.profile.career_level if hasattr(user, 'profile') else 'mid',
            'min_match_score': 70,
            'max_jobs_per_day': user.daily_application_limit,
        }
        
        self.user_preferences_cache[cache_key] = preferences
        return preferences
    
    async def store_jobs_for_user(self, user, jobs):
        """Store scraped jobs for user"""
        
        from backend.apps.job_search.models import ScrapedJob
        
        for job in jobs[:50]:  # Store top 50 jobs
            try:
                ScrapedJob.objects.update_or_create(
                    user=user,
                    job_id=job.get('job_id'),
                    source=job.get('source'),
                    defaults={
                        'title': job.get('title'),
                        'company': job.get('company'),
                        'location': job.get('location'),
                        'description': job.get('description'),
                        'salary': job.get('salary'),
                        'job_type': job.get('job_type'),
                        'experience_level': job.get('experience_level'),
                        'apply_url': job.get('apply_url'),
                        'posted_date': job.get('posted_date'),
                        'match_score': job.get('match_score', 0),
                        'match_reasons': job.get('match_reasons', []),
                        'is_applied': False,
                        'is_saved': job.get('match_score', 0) >= 80,
                    }
                )
            except Exception as e:
                logger.error(f"Error storing job for user {user.id}: {e}")
    
    async def notify_user_of_new_jobs(self, user, jobs):
        """Notify user of new high-matching jobs"""
        
        from backend.apps.communications.services import WhatsAppService
        
        high_match_jobs = [j for j in jobs if j.get('match_score', 0) >= 85]
        
        if high_match_jobs:
            whatsapp = WhatsAppService()
            
            message = f"🎯 *New Job Matches Found!*\n\n"
            message += f"We found {len(high_match_jobs)} new jobs matching your profile:\n\n"
            
            for i, job in enumerate(high_match_jobs[:3], 1):
                message += f"{i}. *{job['title']}*\n"
                message += f"   🏢 {job['company']}\n"
                message += f"   📍 {job['location']}\n"
                message += f"   ⭐ Match: {job['match_score']}%\n\n"
            
            message += "Log in to your dashboard to view all matches and apply!"
            
            await whatsapp.send_message(user.whatsapp_number or user.phone_number, message)

class BaseScraper:
    """Base scraper class"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def scrape(self, preferences):
        """Scrape jobs - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def get_session(self):
        """Get aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def parse_salary(self, salary_text):
        """Parse salary text to numeric range"""
        # Implement salary parsing logic
        return None
    
    def parse_date(self, date_text):
        """Parse date text to datetime"""
        # Implement date parsing logic
        return datetime.now()

class Careers24Scraper(BaseScraper):
    """Careers24.co.za scraper"""
    
    async def scrape(self, preferences):
        """Scrape Careers24"""
        
        jobs = []
        base_url = "https://www.careers24.com/jobs/"
        
        # Build search URL based on preferences
        search_params = {
            'keywords': ' '.join(preferences.get('keywords', [])[:3]),
            'location': preferences.get('locations', ['South Africa'])[0],
            'page': 1,
        }
        
        try:
            session = await self.get_session()
            
            for page in range(1, 4):  # Scrape first 3 pages
                search_params['page'] = page
                url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in search_params.items() if v)}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        page_jobs = self.parse_page(html)
                        jobs.extend(page_jobs)
                        
                        if len(page_jobs) < 20:  # Less than full page
                            break
                    
                    await asyncio.sleep(1)  # Be polite
            
        except Exception as e:
            logger.error(f"Error scraping Careers24: {e}")
        
        return jobs
    
    def parse_page(self, html):
        """Parse Careers24 job listings"""
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        job_listings = soup.find_all('div', class_='job-card')  # Update selector
        
        for listing in job_listings:
            try:
                job = {
                    'source': 'careers24',
                    'job_id': self.extract_job_id(listing),
                    'title': self.extract_title(listing),
                    'company': self.extract_company(listing),
                    'location': self.extract_location(listing),
                    'description': self.extract_description(listing),
                    'salary': self.extract_salary(listing),
                    'job_type': self.extract_job_type(listing),
                    'experience_level': self.extract_experience_level(listing),
                    'apply_url': self.extract_apply_url(listing),
                    'posted_date': self.extract_posted_date(listing),
                }
                
                if job['title'] and job['company']:
                    jobs.append(job)
            
            except Exception as e:
                logger.debug(f"Error parsing job listing: {e}")
                continue
        
        return jobs
    
    def extract_job_id(self, element):
        """Extract job ID"""
        # Implementation specific to Careers24
        return None
    
    def extract_title(self, element):
        """Extract job title"""
        # Implementation specific to Careers24
        return None
    
    # Implement other extraction methods...

class PNetScraper(BaseScraper):
    """PNet.co.za scraper"""
    
    async def scrape(self, preferences):
        """Scrape PNet"""
        # Similar implementation to Careers24Scraper
        return []

class IndeedScraper(BaseScraper):
    """Indeed.co.za scraper"""
    
    async def scrape(self, preferences):
        """Scrape Indeed"""
        # Similar implementation to Careers24Scraper
        return []

# Implement other scrapers...
