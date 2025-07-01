from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import asyncio
from enum import Enum
import pandas as pd
import io
import requests
import aiohttp
from playwright.async_api import async_playwright
import time
import random
from urllib.parse import quote

# Set Playwright browsers path
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"

class Credentials(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    hunter_api_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CredentialsUpdate(BaseModel):
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    hunter_api_key: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    llm_provider: LLMProvider = LLMProvider.OPENAI
    max_results: int = 50

class ParsedQuery(BaseModel):
    roles: List[str]
    locations: List[str]
    company_size_min: Optional[int] = None
    company_size_max: Optional[int] = None
    industries: List[str] = []
    seniority_levels: List[str] = []

class LinkedInProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    job_title: str
    company_name: str
    company_website: Optional[str] = None
    linkedin_profile_url: str
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    industry: Optional[str] = None
    location: str
    company_size: Optional[str] = None
    seniority_level: Optional[str] = None
    decision_maker_indicator: bool = False
    engagement_score: float = 0.0
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class ScrapingJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str
    parsed_query: ParsedQuery
    status: str = "pending"  # pending, running, completed, failed
    profiles_found: int = 0
    total_profiles: List[LinkedInProfile] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

# LLM Service
class LLMService:
    def __init__(self):
        self.providers = {}
    
    async def parse_query(self, query: str, provider: LLMProvider, api_key: str) -> ParsedQuery:
        """Parse natural language query using specified LLM provider"""
        prompt = f"""
        Parse this natural language query for LinkedIn lead generation into structured parameters.
        Query: "{query}"
        
        Extract and return JSON with these fields:
        - roles: List of job titles/roles to search for
        - locations: List of geographic locations
        - company_size_min: Minimum company size (number of employees)
        - company_size_max: Maximum company size (number of employees)
        - industries: List of industry names
        - seniority_levels: List of seniority levels (manager, director, vp, etc.)
        
        Example output:
        {{
            "roles": ["Vendor Manager", "Head of Digital Transformation"],
            "locations": ["United States", "US"],
            "company_size_min": 500,
            "company_size_max": null,
            "industries": [],
            "seniority_levels": ["Manager", "Head"]
        }}
        """
        
        try:
            if provider == LLMProvider.OPENAI:
                return await self._parse_with_openai(prompt, api_key)
            elif provider == LLMProvider.CLAUDE:
                return await self._parse_with_claude(prompt, api_key)
            elif provider == LLMProvider.GEMINI:
                return await self._parse_with_gemini(prompt, api_key)
        except Exception as e:
            logging.error(f"LLM parsing failed: {str(e)}")
            # Fallback to basic parsing
            return ParsedQuery(
                roles=["Manager", "Director"],
                locations=["United States"],
                company_size_min=100,
                industries=[],
                seniority_levels=["Manager"]
            )
    
    async def _parse_with_openai(self, prompt: str, api_key: str) -> ParsedQuery:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                   headers=headers, json=payload) as response:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                    return ParsedQuery(**parsed_data)
                
                raise Exception("Failed to parse OpenAI response")
    
    async def _parse_with_claude(self, prompt: str, api_key: str) -> ParsedQuery:
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with session.post("https://api.anthropic.com/v1/messages", 
                                   headers=headers, json=payload) as response:
                result = await response.json()
                content = result['content'][0]['text']
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                    return ParsedQuery(**parsed_data)
                
                raise Exception("Failed to parse Claude response")
    
    async def _parse_with_gemini(self, prompt: str, api_key: str) -> ParsedQuery:
        async with aiohttp.ClientSession() as session:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            
            async with session.post(url, json=payload) as response:
                result = await response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                    return ParsedQuery(**parsed_data)
                
                raise Exception("Failed to parse Gemini response")

# LinkedIn Scraper Service
class LinkedInScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def login(self, email: str, password: str):
        """Login to LinkedIn with provided credentials"""
        playwright = await async_playwright().start()
        
        # Try different browser options for better compatibility
        try:
            # First try chromium with explicit executable path
            self.browser = await playwright.chromium.launch(
                headless=True,
                executable_path="/pw-browsers/chromium-1169/chrome-linux/chrome",
                args=[
                    '--no-sandbox',
                    '--disable-bounding-box-limits',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-gpu'
                ]
            )
        except Exception as e:
            logging.warning(f"Chromium with explicit path failed: {str(e)}, trying default chromium...")
            try:
                # Try default chromium
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-bounding-box-limits',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-gpu'
                    ]
                )
            except Exception as e2:
                logging.warning(f"Default chromium failed: {str(e2)}, trying Firefox...")
                try:
                    # Fallback to Firefox
                    self.browser = await playwright.firefox.launch(
                        headless=True,
                        args=['--no-sandbox']
                    )
                except Exception as e3:
                    logging.error(f"All browsers failed. Chromium: {str(e)}, Default: {str(e2)}, Firefox: {str(e3)}")
                    raise Exception(f"Failed to launch any browser. Try installing browsers with: playwright install")
        
        # Create context with realistic user agent
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = await self.context.new_page()
        
        # Navigate to LinkedIn login
        await self.page.goto('https://www.linkedin.com/login')
        await self.page.wait_for_load_state('networkidle')
        
        # Fill login form
        await self.page.fill('#username', email)
        await self.page.fill('#password', password)
        
        # Add random delay to mimic human behavior
        await asyncio.sleep(random.uniform(1, 3))
        
        # Click login
        await self.page.click('button[type="submit"]')
        await self.page.wait_for_load_state('networkidle')
        
        # Check if login was successful
        current_url = self.page.url
        if 'feed' in current_url or 'in/' in current_url:
            logging.info("LinkedIn login successful")
            return True
        else:
            logging.error("LinkedIn login failed")
            return False
    
    async def search_profiles(self, parsed_query: ParsedQuery, max_results: int = 50) -> List[LinkedInProfile]:
        """Search LinkedIn profiles based on parsed query"""
        if not self.page:
            raise Exception("Must login first")
        
        profiles = []
        
        try:
            # Construct search URL
            search_terms = " OR ".join(parsed_query.roles)
            location_terms = " OR ".join(parsed_query.locations) if parsed_query.locations else ""
            
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(search_terms)}"
            if location_terms:
                search_url += f"&geoUrn={quote(location_terms)}"
            
            await self.page.goto(search_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Scroll and load results
            page_count = 0
            max_pages = min(5, (max_results // 10) + 1)
            
            while page_count < max_pages and len(profiles) < max_results:
                # Extract profile data from current page
                profile_elements = await self.page.query_selector_all('.reusable-search__result-container')
                
                for element in profile_elements:
                    if len(profiles) >= max_results:
                        break
                    
                    try:
                        profile_data = await self._extract_profile_data(element)
                        if profile_data and self._matches_criteria(profile_data, parsed_query):
                            profiles.append(profile_data)
                    except Exception as e:
                        logging.warning(f"Failed to extract profile: {str(e)}")
                        continue
                
                # Load next page
                page_count += 1
                try:
                    next_button = await self.page.query_selector('button[aria-label="Next"]')
                    if next_button:
                        await next_button.click()
                        await self.page.wait_for_load_state('networkidle')
                        await asyncio.sleep(random.uniform(2, 4))
                    else:
                        break
                except:
                    break
            
            return profiles
            
        except Exception as e:
            logging.error(f"LinkedIn search failed: {str(e)}")
            return profiles
    
    async def _extract_profile_data(self, element) -> Optional[LinkedInProfile]:
        """Extract profile data from search result element"""
        try:
            # Extract name
            name_element = await element.query_selector('.entity-result__title-text a')
            full_name = (await name_element.inner_text()).strip() if name_element else "Unknown"
            
            # Extract LinkedIn URL
            linkedin_url = await name_element.get_attribute('href') if name_element else ""
            if linkedin_url and not linkedin_url.startswith('http'):
                linkedin_url = f"https://www.linkedin.com{linkedin_url}"
            
            # Extract job title and company
            primary_subtitle = await element.query_selector('.entity-result__primary-subtitle')
            job_title = (await primary_subtitle.inner_text()).strip() if primary_subtitle else "Unknown"
            
            secondary_subtitle = await element.query_selector('.entity-result__secondary-subtitle')
            company_name = (await secondary_subtitle.inner_text()).strip() if secondary_subtitle else "Unknown"
            
            # Extract location
            location_element = await element.query_selector('.entity-result__secondary-subtitle + div')
            location = (await location_element.inner_text()).strip() if location_element else "Unknown"
            
            # Determine seniority level
            seniority_level = self._determine_seniority(job_title)
            
            # Create profile object
            profile = LinkedInProfile(
                full_name=full_name,
                job_title=job_title,
                company_name=company_name,
                linkedin_profile_url=linkedin_url,
                location=location,
                seniority_level=seniority_level,
                decision_maker_indicator=seniority_level in ["Director", "VP", "Head", "Manager"],
                engagement_score=self._calculate_engagement_score(job_title, company_name)
            )
            
            return profile
            
        except Exception as e:
            logging.error(f"Profile extraction failed: {str(e)}")
            return None
    
    def _determine_seniority(self, job_title: str) -> str:
        """Determine seniority level from job title"""
        title_lower = job_title.lower()
        
        if any(word in title_lower for word in ['ceo', 'president', 'founder', 'owner']):
            return "Executive"
        elif any(word in title_lower for word in ['vp', 'vice president', 'svp']):
            return "VP"
        elif any(word in title_lower for word in ['director', 'head of']):
            return "Director"
        elif any(word in title_lower for word in ['manager', 'lead', 'supervisor']):
            return "Manager"
        elif any(word in title_lower for word in ['senior', 'sr.', 'principal']):
            return "Senior"
        else:
            return "Individual Contributor"
    
    def _calculate_engagement_score(self, job_title: str, company_name: str) -> float:
        """Calculate engagement score based on profile data"""
        score = 5.0  # Base score
        
        # Higher score for decision-making roles
        title_lower = job_title.lower()
        if any(word in title_lower for word in ['manager', 'director', 'vp', 'head']):
            score += 2.0
        
        # Higher score for larger/known companies
        if len(company_name) > 5 and not any(word in company_name.lower() for word in ['inc', 'llc', 'corp']):
            score += 1.0
        
        return min(score, 10.0)
    
    def _matches_criteria(self, profile: LinkedInProfile, criteria: ParsedQuery) -> bool:
        """Check if profile matches search criteria"""
        # Check role matching
        if criteria.roles:
            title_match = any(role.lower() in profile.job_title.lower() for role in criteria.roles)
            if not title_match:
                return False
        
        # Check location matching
        if criteria.locations:
            location_match = any(loc.lower() in profile.location.lower() for loc in criteria.locations)
            if not location_match:
                return False
        
        return True
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()

# Global instances
llm_service = LLMService()
scraper = LinkedInScraper()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "LinkedIn Lead Generation Tool API"}

@api_router.post("/credentials", response_model=Credentials)
async def save_credentials(credentials: CredentialsUpdate):
    """Save or update credentials"""
    try:
        # Check if credentials exist
        existing = await db.credentials.find_one({})
        
        if existing:
            # Update existing
            update_data = {k: v for k, v in credentials.dict().items() if v is not None}
            update_data['updated_at'] = datetime.utcnow()
            
            await db.credentials.update_one({}, {"$set": update_data})
            updated = await db.credentials.find_one({})
            return Credentials(**updated)
        else:
            # Create new
            cred_dict = credentials.dict()
            cred_obj = Credentials(**cred_dict)
            await db.credentials.insert_one(cred_obj.dict())
            return cred_obj
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/credentials", response_model=Credentials)
async def get_credentials():
    """Get current credentials (passwords hidden for security)"""
    try:
        credentials = await db.credentials.find_one({})
        if not credentials:
            return Credentials()
        
        # Hide sensitive data
        cred_obj = Credentials(**credentials)
        if cred_obj.linkedin_password:
            cred_obj.linkedin_password = "••••••••"
        
        return cred_obj
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/parse-query", response_model=ParsedQuery)
async def parse_query(query_data: SearchQuery):
    """Parse natural language query using specified LLM"""
    try:
        # Get credentials
        credentials = await db.credentials.find_one({})
        if not credentials:
            raise HTTPException(status_code=400, detail="No credentials configured")
        
        # Get appropriate API key
        if query_data.llm_provider == LLMProvider.OPENAI and not credentials.get('openai_api_key'):
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")
        elif query_data.llm_provider == LLMProvider.CLAUDE and not credentials.get('claude_api_key'):
            raise HTTPException(status_code=400, detail="Claude API key not configured")
        elif query_data.llm_provider == LLMProvider.GEMINI and not credentials.get('gemini_api_key'):
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
        api_key = credentials.get(f'{query_data.llm_provider.value}_api_key')
        parsed_query = await llm_service.parse_query(query_data.query, query_data.llm_provider, api_key)
        
        return parsed_query
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/start-scraping", response_model=ScrapingJob)
async def start_scraping(query_data: SearchQuery, background_tasks: BackgroundTasks):
    """Start LinkedIn scraping job"""
    try:
        # Get credentials
        credentials = await db.credentials.find_one({})
        if not credentials or not credentials.get('linkedin_email') or not credentials.get('linkedin_password'):
            raise HTTPException(status_code=400, detail="LinkedIn credentials not configured")
        
        # Parse query first
        api_key = credentials.get(f'{query_data.llm_provider.value}_api_key')
        if not api_key:
            raise HTTPException(status_code=400, detail=f"{query_data.llm_provider.value} API key not configured")
        
        parsed_query = await llm_service.parse_query(query_data.query, query_data.llm_provider, api_key)
        
        # Create scraping job
        job = ScrapingJob(
            original_query=query_data.query,
            parsed_query=parsed_query,
            status="pending"
        )
        
        # Save job to database
        await db.scraping_jobs.insert_one(job.dict())
        
        # Start background scraping
        background_tasks.add_task(
            perform_scraping,
            job.id,
            credentials['linkedin_email'],
            credentials['linkedin_password'],
            parsed_query,
            query_data.max_results
        )
        
        return job
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def perform_scraping(job_id: str, email: str, password: str, parsed_query: ParsedQuery, max_results: int):
    """Background task to perform LinkedIn scraping"""
    try:
        # Update job status
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "running"}}
        )
        
        # Initialize scraper
        scraper = LinkedInScraper()
        
        # Login to LinkedIn
        login_success = await scraper.login(email, password)
        if not login_success:
            raise Exception("LinkedIn login failed")
        
        # Perform search
        profiles = await scraper.search_profiles(parsed_query, max_results)
        
        # Update job with results
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "profiles_found": len(profiles),
                    "total_profiles": [profile.dict() for profile in profiles],
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        # Save individual profiles
        for profile in profiles:
            await db.profiles.insert_one(profile.dict())
        
        await scraper.close()
        
    except Exception as e:
        logging.error(f"Scraping job {job_id} failed: {str(e)}")
        await db.scraping_jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow()
                }
            }
        )

@api_router.get("/scraping-jobs", response_model=List[ScrapingJob])
async def get_scraping_jobs():
    """Get all scraping jobs"""
    try:
        jobs = await db.scraping_jobs.find().sort("created_at", -1).limit(50).to_list(50)
        return [ScrapingJob(**job) for job in jobs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scraping-jobs/{job_id}", response_model=ScrapingJob)
async def get_scraping_job(job_id: str):
    """Get specific scraping job"""
    try:
        job = await db.scraping_jobs.find_one({"id": job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return ScrapingJob(**job)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/export-csv/{job_id}")
async def export_csv(job_id: str):
    """Export scraping job results as CSV"""
    try:
        job = await db.scraping_jobs.find_one({"id": job_id})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Convert profiles to DataFrame
        profiles_data = job['total_profiles']
        if not profiles_data:
            raise HTTPException(status_code=400, detail="No profiles found")
        
        df = pd.DataFrame(profiles_data)
        
        # Reorder columns to match requirements
        column_order = [
            'full_name', 'job_title', 'company_name', 'company_website',
            'linkedin_profile_url', 'email_address', 'phone_number',
            'industry', 'location', 'company_size', 'seniority_level',
            'decision_maker_indicator', 'engagement_score'
        ]
        
        # Ensure all columns exist
        for col in column_order:
            if col not in df.columns:
                df[col] = None
        
        df = df[column_order]
        
        # Create CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Return as file download
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename=linkedin_leads_{job_id}.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()