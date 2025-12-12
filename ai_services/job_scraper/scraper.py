# ai_services/job_scraper/scraper.py
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import aiohttp

class JobScraper:
    def __init__(self):
        self.sites = [
            'careers24.com',
            'pnet.co.za',
            'indeed.co.za',
            'careerjunction.co.za',
            'linkedin.com/jobs'
        ]
        
    async def scrape_jobs(self, user_profile):
        """Scrape jobs twice daily using AI matching"""
        jobs = []
        
        for site in self.sites:
            site_jobs = await self.scrape_site(site, user_profile)
            jobs.extend(site_jobs)
            
        # AI matching algorithm
        matched_jobs = self.ai_match_jobs(jobs, user_profile)
        return matched_jobs
        
    def ai_match_jobs(self, jobs, user_profile):
        """AI-powered job matching"""
        # Use embeddings and cosine similarity
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        user_embedding = model.encode(user_profile.skills)
        
        matched = []
        for job in jobs:
            job_embedding = model.encode(job['description'])
            similarity = cosine_similarity([user_embedding], [job_embedding])[0][0]
            
            if similarity > 0.75:  # Threshold
                job['match_score'] = similarity
                matched.append(job)
                
        return sorted(matched, key=lambda x: x['match_score'], reverse=True)
