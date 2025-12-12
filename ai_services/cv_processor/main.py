# ai_services/cv_processor/main.py
import openai
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import cv2
from PIL import Image

class CVEnhancer:
    def __init__(self):
        self.llm = OpenAI(temperature=0.7)
        self.template = """
        Enhance the following CV for South African job market:
        Original: {original_cv}
        
        Requirements:
        1. Professional tone for SA market
        2. Include relevant keywords
        3. Optimize for ATS systems
        4. Format in reverse chronological order
        5. Highlight achievements with metrics
        
        Enhanced CV:"""
        
    def process_cv(self, cv_text, user_profile):
        prompt = PromptTemplate(
            input_variables=["original_cv"],
            template=self.template
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)
        enhanced_cv = chain.run(original_cv=cv_text)
        
        # Add photo and qualifications
        final_doc = self.create_final_document(
            enhanced_cv,
            user_profile.photo,
            user_profile.qualifications
        )
        
        return final_doc
