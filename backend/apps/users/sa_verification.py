"""
South African ID verification module
"""
import requests
from django.conf import settings
from django.core.cache import cache
import hashlib

class SAIdentityVerifier:
    """Verify South African identity documents"""
    
    @staticmethod
    def validate_id_number(id_number):
        """
        Validate SA ID number using Luhn algorithm and other checks
        """
        if not id_number or len(str(id_number)) != 13:
            return False
        
        id_str = str(id_number)
        
        # Check if all digits are numeric
        if not id_str.isdigit():
            return False
        
        # Luhn algorithm (Modulus 10)
        total = 0
        for i in range(12):
            digit = int(id_str[i])
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(id_str[-1])
    
    @staticmethod
    def extract_demographics(id_number):
        """
        Extract demographics from SA ID number
        """
        id_str = str(id_number)
        
        # Extract date of birth
        year = int(id_str[0:2])
        month = int(id_str[2:4])
        day = int(id_str[4:6])
        
        # Determine century
        current_year = 2000 + (year % 100)
        if year <= 22:  # Assuming 2022 as current year for century determination
            birth_year = 2000 + year
        else:
            birth_year = 1900 + year
        
        # Extract gender from 7th digit
        gender_digit = int(id_str[6:10])
        gender = "Female" if gender_digit < 5000 else "Male"
        
        # Extract citizenship status (0 = SA citizen, 1 = permanent resident)
        citizenship = "SA Citizen" if id_str[10] == '0' else "Permanent Resident"
        
        return {
            'date_of_birth': f"{birth_year}-{month:02d}-{day:02d}",
            'gender': gender,
            'citizenship_status': citizenship,
            'raw_id': id_number
        }
    
    @staticmethod
    def verify_against_home_affairs(id_number, full_name):
        """
        Verify ID against Home Affairs database (placeholder for actual integration)
        Note: Actual integration requires proper authorization and compliance
        """
        # This is a placeholder for actual Home Affairs API integration
        # In production, this would require proper legal agreements and API access
        
        cache_key = f"home_affairs_verify_{hashlib.md5(f'{id_number}_{full_name}'.encode()).hexdigest()}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Simulated verification (replace with actual API call)
        # For now, we'll just validate the ID number format
        is_valid = SAIdentityVerifier.validate_id_number(id_number)
        
        result = {
            'verified': is_valid,
            'timestamp': '2024-01-01T00:00:00Z',
            'source': 'simulated',
            'confidence': 0.95 if is_valid else 0.0
        }
        
        cache.set(cache_key, result, timeout=86400)  # Cache for 24 hours
        return result

class DocumentVerifier:
    """Verify uploaded documents"""
    
    ALLOWED_DOCUMENT_TYPES = ['id_document', 'proof_of_residence', 'qualification', 'cv', 'photo']
    
    @staticmethod
    def validate_document(document, document_type):
        """
        Validate uploaded document
        """
        if document_type not in DocumentVerifier.ALLOWED_DOCUMENT_TYPES:
            return False, "Invalid document type"
        
        # Check file size
        max_size = 10 * 1024 * 1024  # 10MB
        if document.size > max_size:
            return False, f"File size exceeds {max_size/1024/1024}MB limit"
        
        # Check file extension
        allowed_extensions = {
            'id_document': ['.pdf', '.jpg', '.jpeg', '.png'],
            'proof_of_residence': ['.pdf', '.jpg', '.jpeg', '.png'],
            'qualification': ['.pdf', '.jpg', '.jpeg', '.png'],
            'cv': ['.pdf', '.doc', '.docx'],
            'photo': ['.jpg', '.jpeg', '.png']
        }
        
        import os
        ext = os.path.splitext(document.name)[1].lower()
        if ext not in allowed_extensions.get(document_type, []):
            return False, f"Invalid file extension for {document_type}"
        
        # Check for malware (placeholder for actual scanner)
        # In production, integrate with virus scanner
        is_safe = DocumentVerifier.scan_for_malware(document)
        if not is_safe:
            return False, "File failed security scan"
        
        return True, "Document validated successfully"
    
    @staticmethod
    def scan_for_malware(document):
        """
        Scan document for malware (placeholder)
        """
        # In production, integrate with ClamAV or similar
        # For now, return True for all files
        return True
    
    @staticmethod
    def extract_text_from_document(document):
        """
        Extract text from various document types
        """
        import PyPDF2
        from PIL import Image
        import pytesseract
        
        text = ""
        
        if document.name.endswith('.pdf'):
            # Extract from PDF
            pdf_reader = PyPDF2.PdfReader(document)
            for page in pdf_reader.pages:
                text += page.extract_text()
        
        elif document.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Extract from image using OCR
            image = Image.open(document)
            text = pytesseract.image_to_string(image)
        
        return text.strip()
