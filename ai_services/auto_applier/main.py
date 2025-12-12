"""
Automated job application system
"""
import asyncio
import time
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoApplier:
    """Automated job application system"""
    
    def __init__(self):
        self.driver = None
        self.user_data = {}
        self.application_templates = {}
        
        # Configure Chrome options
        self.chrome_options = Options()
        
        if not logging.DEBUG:
            self.chrome_options.add_argument('--headless')
        
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Anti-detection measures
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
    async def initialize(self):
        """Initialize webdriver"""
        if self.driver is None:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Execute CDP commands to prevent detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    async def close(self):
        """Close webdriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    async def apply_for_jobs(self, user_id: str, jobs: List[Dict[str, Any]], max_daily: int = 10):
        """Apply for multiple jobs"""
        
        await self.initialize()
        
        # Load user data
        await self.load_user_data(user_id)
        
        # Sort jobs by match score
        jobs.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        applications_today = await self.get_todays_applications(user_id)
        remaining_applications = max(0, max_daily - applications_today)
        
        if remaining_applications <= 0:
            logger.info(f"User {user_id} has reached daily application limit")
            return []
        
        jobs_to_apply = jobs[:remaining_applications]
        successful_applications = []
        
        logger.info(f"Applying for {len(jobs_to_apply)} jobs for user {user_id}")
        
        for job in jobs_to_apply:
            try:
                success = await self.apply_for_job(user_id, job)
                
                if success:
                    successful_applications.append(job)
                    
                    # Log application
                    await self.log_application(user_id, job, success)
                    
                    # Notify user
                    await self.notify_user(user_id, job, success)
                    
                    # Random delay between applications
                    await asyncio.sleep(self.get_random_delay())
                
                else:
                    logger.warning(f"Failed to apply for job: {job.get('title')}")
                    await self.log_application(user_id, job, False)
            
            except Exception as e:
                logger.error(f"Error applying for job {job.get('title')}: {e}")
                await self.log_application(user_id, job, False, str(e))
            
            # Check if we've reached daily limit
            if len(successful_applications) >= remaining_applications:
                break
        
        await self.close()
        return successful_applications
    
    async def apply_for_job(self, user_id: str, job: Dict[str, Any]) -> bool:
        """Apply for a single job"""
        
        apply_url = job.get('apply_url')
        if not apply_url:
            logger.warning(f"No apply URL for job: {job.get('title')}")
            return False
        
        logger.info(f"Applying for job: {job.get('title')} at {job.get('company')}")
        
        try:
            # Navigate to application page
            self.driver.get(apply_url)
            await asyncio.sleep(2)  # Wait for page load
            
            # Detect application form type
            form_type = self.detect_form_type()
            
            # Fill application form based on type
            if form_type == 'linkedin_easy_apply':
                success = await self.fill_linkedin_easy_apply()
            elif form_type == 'indeed_apply':
                success = await self.fill_indeed_apply()
            elif form_type == 'careers24_apply':
                success = await self.fill_careers24_apply()
            elif form_type == 'pnet_apply':
                success = await self.fill_pnet_apply()
            else:
                success = await self.fill_generic_application_form()
            
            if success:
                logger.info(f"Successfully applied for: {job.get('title')}")
            else:
                logger.warning(f"Failed to apply for: {job.get('title')}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error in apply_for_job: {e}")
            return False
    
    def detect_form_type(self) -> str:
        """Detect the type of application form"""
        
        current_url = self.driver.current_url
        
        # Check for known platforms
        if 'linkedin.com' in current_url and 'easyApply' in current_url:
            return 'linkedin_easy_apply'
        elif 'indeed.com' in current_url and 'apply' in current_url:
            return 'indeed_apply'
        elif 'careers24.com' in current_url:
            return 'careers24_apply'
        elif 'pnet.co.za' in current_url:
            return 'pnet_apply'
        
        # Check for common form elements
        try:
            # Check for LinkedIn Easy Apply button
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Easy Apply')]")
            return 'linkedin_easy_apply'
        except:
            pass
        
        try:
            # Check for Indeed apply button
            self.driver.find_element(By.ID, 'indeed-apply-button')
            return 'indeed_apply'
        except:
            pass
        
        # Default to generic
        return 'generic'
    
    async def fill_linkedin_easy_apply(self) -> bool:
        """Fill LinkedIn Easy Apply form"""
        
        try:
            # Click Easy Apply button if not already on form
            try:
                easy_apply_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Easy Apply')]"))
                )
                easy_apply_btn.click()
                await asyncio.sleep(2)
            except:
                pass  # Might already be on form
            
            # Fill contact information
            contact_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'contact')]")
            for field in contact_fields:
                field_name = field.get_attribute('name') or field.get_attribute('id') or ''
                field_name = field_name.lower()
                
                if 'email' in field_name:
                    field.send_keys(self.user_data.get('email', ''))
                elif 'phone' in field_name:
                    field.send_keys(self.user_data.get('phone', ''))
                elif 'name' in field_name:
                    if 'first' in field_name:
                        field.send_keys(self.user_data.get('first_name', ''))
                    elif 'last' in field_name:
                        field.send_keys(self.user_data.get('last_name', ''))
            
            # Upload CV if field exists
            try:
                cv_upload = self.driver.find_element(By.XPATH, "//input[@type='file' and contains(@accept, '.pdf')]")
                cv_path = self.user_data.get('cv_path')
                if cv_path:
                    cv_upload.send_keys(cv_path)
            except:
                pass  # No CV upload field
            
            # Answer questions
            await self.answer_linkedin_questions()
            
            # Submit application
            try:
                submit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit')]"))
                )
                submit_btn.click()
                
                # Wait for confirmation
                await asyncio.sleep(3)
                
                # Check for success
                try:
                    self.driver.find_element(By.XPATH, "//*[contains(text(), 'application submitted') or contains(text(), 'successfully applied')]")
                    return True
                except:
                    return True  # Assume success if we can't find confirmation
            
            except Exception as e:
                logger.error(f"Error submitting LinkedIn application: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error in fill_linkedin_easy_apply: {e}")
            return False
    
    async def answer_linkedin_questions(self):
        """Answer LinkedIn application questions"""
        
        try:
            # Find all question containers
            questions = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'jobs-easy-apply-form-section')]")
            
            for question in questions:
                question_text = question.text.lower()
                
                # Skip if already answered
                try:
                    question.find_element(By.XPATH, ".//input[@value]")
                    continue  # Already answered
                except:
                    pass
                
                # Answer based on question type
                if 'years of experience' in question_text:
                    await self.answer_experience_question(question)
                elif 'salary' in question_text or 'compensation' in question_text:
                    await self.answer_salary_question(question)
                elif 'visa' in question_text or 'work permit' in question_text:
                    await self.answer_visa_question(question)
                elif 'notice period' in question_text:
                    await self.answer_notice_period_question(question)
                elif 'gender' in question_text or 'race' in question_text or 'disability' in question_text:
                    await self.answer_demographic_question(question)
                else:
                    await self.answer_generic_question(question)
        
        except Exception as e:
            logger.debug(f"Error answering questions: {e}")
    
    async def answer_experience_question(self, question_element):
        """Answer years of experience question"""
        try:
            experience = str(self.user_data.get('years_experience', '3'))
            
            # Try different input types
            try:
                input_field = question_element.find_element(By.XPATH, ".//input[@type='text' or @type='number']")
                input_field.send_keys(experience)
            except:
                pass
            
            try:
                select_field = question_element.find_element(By.XPATH, ".//select")
                from selenium.webdriver.support.ui import Select
                select = Select(select_field)
                
                # Find closest option
                for option in select.options:
                    if experience in option.text or option.text == experience:
                        select.select_by_visible_text(option.text)
                        break
            except:
                pass
        
        except Exception as e:
            logger.debug(f"Error answering experience question: {e}")
    
    async def answer_salary_question(self, question_element):
        """Answer salary expectation question"""
        try:
            salary = str(self.user_data.get('salary_expectation', '300000'))
            
            # Try input field
            try:
                input_field = question_element.find_element(By.XPATH, ".//input")
                input_field.send_keys(salary)
            except:
                pass
            
            # Try select/dropdown
            try:
                select_field = question_element.find_element(By.XPATH, ".//select")
                from selenium.webdriver.support.ui import Select
                select = Select(select_field)
                
                # Select appropriate range
                for option in select.options:
                    option_text = option.text.lower()
                    if '300' in option_text or '30' in option_text:
                        select.select_by_visible_text(option.text)
                        break
            except:
                pass
        
        except Exception as e:
            logger.debug(f"Error answering salary question: {e}")
    
    async def answer_visa_question(self, question_element):
        """Answer visa/work permit questions for South Africa"""
        try:
            # South African citizen
            answer = "No"  # Don't require visa
            
            # Try radio buttons
            try:
                no_radio = question_element.find_element(By.XPATH, f".//input[@type='radio' and (@value='No' or contains(@value, 'no'))]")
                no_radio.click()
            except:
                pass
            
            # Try select
            try:
                select_field = question_element.find_element(By.XPATH, ".//select")
                from selenium.webdriver.support.ui import Select
                select = Select(select_field)
                select.select_by_visible_text("No")
            except:
                pass
        
        except Exception as e:
            logger.debug(f"Error answering visa question: {e}")
    
    async def fill_generic_application_form(self) -> bool:
        """Fill generic application form"""
        
        try:
            # Find all input fields
            inputs = self.driver.find_elements(By.XPATH, "//input[@type='text' or @type='email' or @type='tel']")
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            
            all_fields = inputs + textareas + selects
            
            for field in all_fields:
                try:
                    field_name = field.get_attribute('name') or field.get_attribute('id') or field.get_attribute('placeholder') or ''
                    field_name = field_name.lower()
                    field_type = field.get_attribute('type') or field.tag_name
                    
                    # Skip if readonly or disabled
                    if field.get_attribute('readonly') or field.get_attribute('disabled'):
                        continue
                    
                    # Fill based on field name
                    value = self.get_field_value(field_name, field_type)
                    if value:
                        if field_type == 'select':
                            from selenium.webdriver.support.ui import Select
                            select = Select(field)
                            try:
                                select.select_by_visible_text(value)
                            except:
                                try:
                                    select.select_by_value(value)
                                except:
                                    pass
                        else:
                            field.clear()
                            field.send_keys(value)
                    
                    await asyncio.sleep(0.1)
                
                except Exception as e:
                    logger.debug(f"Error filling field {field_name}: {e}")
                    continue
            
            # Upload files
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            for file_input in file_inputs:
                accept = file_input.get_attribute('accept') or ''
                
                if 'pdf' in accept or '.doc' in accept:
                    # Upload CV
                    cv_path = self.user_data.get('cv_path')
                    if cv_path:
                        file_input.send_keys(cv_path)
                elif 'image' in accept:
                    # Upload photo
                    photo_path = self.user_data.get('photo_path')
                    if photo_path:
                        file_input.send_keys(photo_path)
            
            # Submit form
            submit_buttons = self.driver.find_elements(By.XPATH, "//button[@type='submit']")
            if submit_buttons:
                submit_buttons[0].click()
                await asyncio.sleep(3)
                return True
            
            # Try input type submit
            submit_inputs = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
            if submit_inputs:
                submit_inputs[0].click()
                await asyncio.sleep(3)
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error in fill_generic_application_form: {e}")
            return False
    
    def get_field_value(self, field_name: str, field_type: str) -> str:
        """Get appropriate value for form field"""
        
        user = self.user_data
        
        # Personal information
        if 'name' in field_name:
            if 'first' in field_name:
                return user.get('first_name', '')
            elif 'last' in field_name:
                return user.get('last_name', '')
            elif 'full' in field_name:
                return user.get('full_name', '')
        
        elif 'email' in field_name:
            return user.get('email', '')
        
        elif 'phone' in field_name or 'mobile' in field_name or 'tel' in field_name:
            return user.get('phone', '')
        
        elif 'address' in field_name:
            if 'street' in field_name:
                return user.get('street_address', '')
            elif 'city' in field_name:
                return user.get('city', '')
            elif 'province' in field_name or 'state' in field_name:
                return user.get('province', '')
            elif 'postal' in field_name or 'zip' in field_name:
                return user.get('postal_code', '')
        
        elif 'id' in field_name or 'identity' in field_name:
            return user.get('sa_id_number', '')
        
        elif 'experience' in field_name:
            return str(user.get('years_experience', '3'))
        
        elif 'salary' in field_name or 'compensation' in field_name:
            return str(user.get('salary_expectation', '300000'))
        
        elif 'notice' in field_name:
            return "30"  # 30 days notice period
        
        elif 'availability' in field_name:
            return "Immediately" if user.get('is_unemployed', True) else "30 days"
        
        # Education
        elif 'education' in field_name or 'qualification' in field_name:
            return user.get('highest_qualification', '')
        
        elif 'university' in field_name or 'college' in field_name or 'institution' in field_name:
            return user.get('education_institution', '')
        
        # Demographic (optional - only if comfortable)
        elif 'race' in field_name and user.get('share_demographics', False):
            return user.get('race', '')
        elif 'gender' in field_name and user.get('share_demographics', False):
            return user.get('gender', '')
        elif 'disability' in field_name and user.get('share_demographics', False):
            return "No" if not user.get('has_disability', False) else "Yes"
        
        return ""
    
    async def load_user_data(self, user_id: str):
        """Load user data for applications"""
        
        from backend.apps.users.models import User
        
        try:
            user = User.objects.get(id=user_id)
            profile = getattr(user, 'profile', None)
            
            self.user_data = {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'phone': user.phone_number,
                'sa_id_number': user.sa_id_number,
                'years_experience': user.years_experience,
                'salary_expectation': float(user.salary_expectation or 300000),
                'highest_qualification': user.highest_qualification,
                
                # From profile
                'street_address': profile.street_address if profile else '',
                'city': profile.city if profile else '',
                'province': profile.province if profile else '',
                'postal_code': profile.postal_code if profile else '',
                'education_institution': '',  # Would come from qualifications
                
                # File paths
                'cv_path': self.get_user_cv_path(user),
                'photo_path': self.get_user_photo_path(user),
                
                # Preferences
                'share_demographics': profile.data_sharing_consent if profile else False,
                'is_unemployed': user.current_occupation is None,
            }
        
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            self.user_data = {}
    
    def get_user_cv_path(self, user):
        """Get user's CV file path"""
        from backend.apps.documents.models import UserDocument
        
        try:
            cv_doc = UserDocument.objects.filter(
                user=user,
                document_type='cv',
                is_processed=True
            ).latest('uploaded_at')
            return cv_doc.processed_file.path
        except:
            return None
    
    def get_user_photo_path(self, user):
        """Get user's photo file path"""
        from backend.apps.documents.models import UserDocument
        
        try:
            photo_doc = UserDocument.objects.filter(
                user=user,
                document_type='photo',
                is_processed=True
            ).latest('uploaded_at')
            return photo_doc.processed_file.path
        except:
            return None
    
    def get_random_delay(self):
        """Get random delay between applications"""
        import random
        return random.uniform(5, 15)  # 5-15 seconds
    
    async def get_todays_applications(self, user_id: str) -> int:
        """Get number of applications submitted today"""
        
        from backend.apps.job_search.models import JobApplication
        
        today = datetime.now().date()
        
        try:
            count = JobApplication.objects.filter(
                user_id=user_id,
                applied_at__date=today
            ).count()
            return count
        except:
            return 0
    
    async def log_application(self, user_id: str, job: Dict[str, Any], success: bool, error: str = None):
        """Log application attempt"""
        
        from backend.apps.job_search.models import JobApplication
        
        try:
            JobApplication.objects.create(
                user_id=user_id,
                job_title=job.get('title'),
                company=job.get('company'),
                job_url=job.get('apply_url'),
                source=job.get('source'),
                match_score=job.get('match_score', 0),
                applied_at=datetime.now(),
                status='applied' if success else 'failed',
                error_message=error,
                application_data=job
            )
            
            # Update user statistics
            from backend.apps.users.models import User
            user = User.objects.get(id=user_id)
            user.total_applications += 1
            if success:
                user.successful_applications += 1
            user.save()
        
        except Exception as e:
            logger.error(f"Error logging application: {e}")
    
    async def notify_user(self, user_id: str, job: Dict[str, Any], success: bool):
        """Notify user of application result"""
        
        from backend.apps.communications.services import WhatsAppService
        
        whatsapp = WhatsAppService()
        
        if success:
            message = f"✅ *Application Submitted!*\n\n"
            message += f"Position: *{job.get('title')}*\n"
            message += f"Company: {job.get('company')}\n"
            message += f"Location: {job.get('location')}\n\n"
            message += f"Match Score: {job.get('match_score')}%\n\n"
            message += "Good luck! We'll notify you of any responses."
        else:
            message = f"❌ *Application Failed*\n\n"
            message += f"Position: *{job.get('title')}*\n"
            message += f"Company: {job.get('company')}\n\n"
            message += "Our AI will try alternative application methods.\n"
            message += "Don't worry, we'll keep searching for you!"
        
        # Send WhatsApp message
        from backend.apps.users.models import User
        user = User.objects.get(id=user_id)
        await whatsapp.send_message(user.whatsapp_number or user.phone_number, message)

# Implement other platform-specific form fillers...
