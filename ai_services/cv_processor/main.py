"""
Main CV processing service
"""
import os
from typing import Dict, Any
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
import openai
from django.conf import settings

class CVEnhancer:
    """Enhance CV using AI"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-4",
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Define prompts
        self.cv_enhancement_prompt = PromptTemplate(
            input_variables=["original_cv", "user_profile", "job_market"],
            template="""
            You are an expert CV writer specializing in the South African job market.
            
            Original CV:
            {original_cv}
            
            User Profile:
            {user_profile}
            
            South African Job Market Context:
            {job_market}
            
            Please enhance this CV following these guidelines:
            
            1. **Professional Formatting**: Use reverse chronological order, clear section headings, and professional language
            2. **ATS Optimization**: Include relevant keywords for Applicant Tracking Systems
            3. **Achievement-Oriented**: Start bullet points with action verbs and include quantifiable achievements
            4. **South African Context**: Tailor to SA business culture and expectations
            5. **Length Optimization**: Keep to 2 pages maximum
            6. **Skills Section**: Categorize skills (Technical, Soft, Industry-Specific)
            7. **Contact Information**: Format professionally
            
            Enhanced CV:
            """
        )
        
        self.cover_letter_prompt = PromptTemplate(
            input_variables=["user_profile", "enhanced_cv", "industry"],
            template="""
            Create a compelling cover letter for a South African job seeker.
            
            User Profile:
            {user_profile}
            
            Enhanced CV Summary:
            {enhanced_cv}
            
            Target Industry: {industry}
            
            Cover Letter Guidelines:
            1. **Professional Format**: Standard business letter format
            2. **Customization**: Generic but adaptable for different roles
            3. **South African Tone**: Professional but approachable
            4. **Key Selling Points**: Highlight 2-3 main strengths
            5. **Call to Action**: Clear next steps
            6. **Length**: 3-4 paragraphs maximum
            
            Cover Letter:
            """
        )
    
    def process_cv(self, cv_text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance CV"""
        
        # Get South African job market context
        job_market_context = self.get_sa_job_market_context()
        
        # Create enhancement chain
        cv_chain = LLMChain(
            llm=self.llm,
            prompt=self.cv_enhancement_prompt
        )
        
        # Enhance CV
        enhanced_cv = cv_chain.run(
            original_cv=cv_text,
            user_profile=str(user_profile),
            job_market=job_market_context
        )
        
        # Generate cover letter
        cover_letter = self.generate_cover_letter(user_profile, enhanced_cv)
        
        # Analyze CV for improvements
        analysis = self.analyze_cv(enhanced_cv, user_profile)
        
        # Calculate savings
        savings = self.calculate_savings(user_profile)
        
        return {
            'enhanced_cv': enhanced_cv,
            'cover_letter': cover_letter,
            'analysis': analysis,
            'savings_calculation': savings,
            'optimization_score': self.calculate_optimization_score(enhanced_cv)
        }
    
    def generate_cover_letter(self, user_profile: Dict[str, Any], enhanced_cv: str) -> str:
        """Generate AI-powered cover letter"""
        
        cover_letter_chain = LLMChain(
            llm=self.llm,
            prompt=self.cover_letter_prompt
        )
        
        industry = user_profile.get('preferred_industries', ['General'])[0]
        
        cover_letter = cover_letter_chain.run(
            user_profile=str(user_profile),
            enhanced_cv=enhanced_cv[:1000],  # First 1000 chars for context
            industry=industry
        )
        
        return cover_letter
    
    def get_sa_job_market_context(self) -> str:
        """Get South African job market context"""
        
        return """
        South African Job Market Characteristics:
        
        1. **Business Culture**: Formal but relationship-oriented, emphasis on Ubuntu philosophy
        2. **Key Industries**: Mining, Finance, Tourism, Agriculture, ICT, Manufacturing
        3. **Employment Trends**: Growing digital economy, emphasis on B-BBEE compliance
        4. **Salary Expectations**: Vary widely by industry and location (Gauteng highest)
        5. **CV Expectations**: 2 pages maximum, professional photo optional, references available on request
        6. **In-Demand Skills**: Digital literacy, project management, data analysis, multilingualism
        7. **Qualifications**: SAQA accreditation important, NQF levels clearly indicated
        """
    
    def analyze_cv(self, cv_text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CV for improvements"""
        
        analysis_prompt = PromptTemplate(
            input_variables=["cv_text", "user_profile"],
            template="""
            Analyze this CV and provide improvement suggestions:
            
            CV:
            {cv_text}
            
            User Profile:
            {user_profile}
            
            Provide analysis in this format:
            
            Strengths: [List 3-5 strengths]
            Areas for Improvement: [List 3-5 areas]
            Keyword Optimization: [List missing keywords]
            ATS Score: [Score out of 100]
            South African Relevance: [Score out of 100]
            """
        )
        
        analysis_chain = LLMChain(
            llm=self.llm,
            prompt=analysis_prompt
        )
        
        analysis_result = analysis_chain.run(
            cv_text=cv_text[:2000],  # Limit text for analysis
            user_profile=str(user_profile)
        )
        
        return self.parse_analysis_result(analysis_result)
    
    def parse_analysis_result(self, analysis_text: str) -> Dict[str, Any]:
        """Parse analysis text into structured data"""
        
        # Simple parsing - in production would use more sophisticated parsing
        lines = analysis_text.split('\n')
        result = {
            'strengths': [],
            'improvements': [],
            'missing_keywords': [],
            'ats_score': 0,
            'sa_relevance_score': 0
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('Strengths:'):
                current_section = 'strengths'
            elif line.startswith('Areas for Improvement:'):
                current_section = 'improvements'
            elif line.startswith('Keyword Optimization:'):
                current_section = 'keywords'
            elif line.startswith('ATS Score:'):
                try:
                    score = int(line.split(':')[1].strip().split()[0])
                    result['ats_score'] = score
                except:
                    pass
            elif line.startswith('South African Relevance:'):
                try:
                    score = int(line.split(':')[1].strip().split()[0])
                    result['sa_relevance_score'] = score
                except:
                    pass
            elif line and current_section and line.startswith('- '):
                item = line[2:].strip()
                if current_section == 'strengths':
                    result['strengths'].append(item)
                elif current_section == 'improvements':
                    result['improvements'].append(item)
                elif current_section == 'keywords':
                    result['missing_keywords'].append(item)
        
        return result
    
    def calculate_savings(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate savings compared to traditional methods"""
        
        # Traditional costs in South Africa
        traditional_costs = {
            'cv_writing': 800,  # R800 for professional CV writing
            'cover_letters': 300,  # R300 per cover letter
            'job_search_time': 2000,  # Estimated value of time spent
            'application_fees': 0,  # Usually free, but time is money
            'career_coaching': 1500,  # Optional career coaching
        }
        
        # CostByte value
        costbyte_value = {
            'cv_enhancement': 800,
            'unlimited_cover_letters': 1000,
            'automated_applications': 3000,
            'time_savings': 2000,
            'ai_optimization': 1000,
        }
        
        total_traditional = sum(traditional_costs.values())
        total_costbyte_value = sum(costbyte_value.values())
        
        savings = total_costbyte_value - 500  # R500 fee
        
        return {
            'traditional_cost': total_traditional,
            'costbyte_value': total_costbyte_value,
            'savings': savings,
            'roi': (savings / 500) * 100,  # ROI percentage
            'breakdown': {
                'cv_writing_saved': traditional_costs['cv_writing'],
                'time_savings': costbyte_value['time_savings'],
                'automation_value': costbyte_value['automated_applications']
            }
        }
    
    def calculate_optimization_score(self, cv_text: str) -> int:
        """Calculate CV optimization score"""
        
        # Simple scoring algorithm
        score = 70  # Base score
        
        # Check for key elements
        key_elements = [
            ('professional summary', 5),
            ('work experience', 10),
            ('education', 10),
            ('skills', 10),
            ('achievements', 10),
            ('quantifiable results', 15),
            ('keywords', 10),
            ('ats_friendly', 10),
        ]
        
        cv_lower = cv_text.lower()
        
        for element, points in key_elements:
            if element in cv_lower:
                score += points
        
        # Check length (optimize for 2 pages)
        word_count = len(cv_text.split())
        if 400 <= word_count <= 800:  # Optimal for 2 pages
            score += 10
        elif word_count > 1000:
            score -= 10
        
        return min(100, score)  # Cap at 100
    
    def generate_cv_variants(self, base_cv: str, industries: list) -> Dict[str, str]:
        """Generate CV variants for different industries"""
        
        variants = {}
        
        for industry in industries[:3]:  # Limit to 3 variants
            variant_prompt = PromptTemplate(
                input_variables=["base_cv", "industry"],
                template="""
                Adapt this CV for the {industry} industry in South Africa:
                
                Base CV:
                {base_cv}
                
                Focus on:
                1. Industry-specific keywords
                2. Relevant skills highlighting
                3. Appropriate achievement emphasis
                4. Industry-standard formatting
                
                Adapted CV for {industry}:
                """
            )
            
            variant_chain = LLMChain(
                llm=self.llm,
                prompt=variant_prompt
            )
            
            variant = variant_chain.run(
                base_cv=base_cv[:1500],
                industry=industry
            )
            
            variants[industry] = variant
        
        return variants
