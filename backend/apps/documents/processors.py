"""
Document processing for CV, photos, and qualifications
"""
import os
import tempfile
from PIL import Image
import PyPDF2
import docx
import pytesseract
from django.conf import settings
from django.core.files.base import ContentFile
import io

class DocumentProcessor:
    """Base document processor"""
    
    def __init__(self):
        self.allowed_extensions = []
        self.max_size = 10 * 1024 * 1024  # 10MB
    
    def validate(self, file):
        """Validate document"""
        if file.size > self.max_size:
            return False, f"File size exceeds {self.max_size/1024/1024}MB"
        
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.allowed_extensions:
            return False, f"Invalid file extension. Allowed: {', '.join(self.allowed_extensions)}"
        
        return True, "Valid"
    
    def process(self, file, user):
        """Process document"""
        raise NotImplementedError

class CVProcessor(DocumentProcessor):
    """CV/Resume processor"""
    
    def __init__(self):
        super().__init__()
        self.allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
    
    def process(self, file, user):
        """Process and enhance CV"""
        
        # Extract text from CV
        cv_text = self.extract_text(file)
        
        # Enhance CV using AI
        enhanced_cv = self.enhance_cv(cv_text, user)
        
        # Generate cover letter
        cover_letter = self.generate_cover_letter(user, enhanced_cv)
        
        # Combine into final document
        final_document = self.create_final_document(enhanced_cv, cover_letter, user)
        
        return {
            'original_text': cv_text,
            'enhanced_cv': enhanced_cv,
            'cover_letter': cover_letter,
            'final_document': final_document
        }
    
    def extract_text(self, file):
        """Extract text from various document formats"""
        
        ext = os.path.splitext(file.name)[1].lower()
        text = ""
        
        if ext == '.pdf':
            # Extract from PDF
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        elif ext in ['.doc', '.docx']:
            # Extract from Word document
            doc = docx.Document(file)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        
        elif ext == '.txt':
            # Read text file
            text = file.read().decode('utf-8')
        
        return text.strip()
    
    def enhance_cv(self, cv_text, user):
        """Enhance CV using AI"""
        
        from ai_services.cv_processor.main import CVEnhancer
        
        enhancer = CVEnhancer()
        enhanced_cv = enhancer.process_cv(cv_text, user)
        
        return enhanced_cv
    
    def generate_cover_letter(self, user, enhanced_cv):
        """Generate AI-powered cover letter"""
        
        from ai_services.cv_processor.cover_letter import CoverLetterGenerator
        
        generator = CoverLetterGenerator()
        cover_letter = generator.generate(user, enhanced_cv)
        
        return cover_letter
    
    def create_final_document(self, cv_text, cover_letter, user):
        """Create final PDF document with CV and cover letter"""
        
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Add user photo if available
        photo_path = self.get_user_photo_path(user)
        if photo_path and os.path.exists(photo_path):
            from reportlab.platypus import Image as ReportLabImage
            photo = ReportLabImage(photo_path, width=100, height=100)
            story.append(photo)
            story.append(Spacer(1, 12))
        
        # Add user details
        story.append(Paragraph(f"<b>{user.get_full_name()}</b>", styles['Title']))
        story.append(Paragraph(user.email, styles['Normal']))
        story.append(Paragraph(user.phone_number, styles['Normal']))
        story.append(Spacer(1, 24))
        
        # Add cover letter
        story.append(Paragraph("<b>Cover Letter</b>", styles['Heading2']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(cover_letter, styles['Normal']))
        story.append(Spacer(1, 24))
        
        # Add CV
        story.append(Paragraph("<b>Curriculum Vitae</b>", styles['Heading2']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(cv_text, styles['Normal']))
        
        doc.build(story)
        
        buffer.seek(0)
        return ContentFile(buffer.read(), name=f"{user.username}_cv.pdf")
    
    def get_user_photo_path(self, user):
        """Get user's photo path"""
        from .models import UserDocument
        try:
            photo_doc = UserDocument.objects.filter(
                user=user,
                document_type='photo',
                is_active=True
            ).latest('uploaded_at')
            return photo_doc.file.path
        except UserDocument.DoesNotExist:
            return None

class PhotoProcessor(DocumentProcessor):
    """Profile photo processor"""
    
    def __init__(self):
        super().__init__()
        self.allowed_extensions = ['.jpg', '.jpeg', '.png']
        self.max_size = 5 * 1024 * 1024  # 5MB
    
    def process(self, file, user):
        """Process and optimize profile photo"""
        
        # Open image
        image = Image.open(file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize to standard dimensions
        target_size = (400, 400)
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Crop to head and shoulders (if possible)
        image = self.crop_head_shoulders(image)
        
        # Enhance image quality
        image = self.enhance_image(image)
        
        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95, optimize=True)
        
        buffer.seek(0)
        return ContentFile(buffer.read(), name=f"{user.username}_photo.jpg")
    
    def crop_head_shoulders(self, image):
        """Crop image to head and shoulders using face detection"""
        
        try:
            import cv2
            import numpy as np
            
            # Convert PIL to OpenCV
            open_cv_image = np.array(image)
            open_cv_image = open_cv_image[:, :, ::-1].copy()  # RGB to BGR
            
            # Load face detector
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Detect faces
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                # Get the largest face
                x, y, w, h = faces[0]
                
                # Calculate crop area (head and shoulders)
                # Extend area above and below face
                head_ratio = 2.5  # Include head and shoulders
                shoulder_ratio = 1.2  # Include shoulders
                
                crop_y = max(0, int(y - h * 0.5))
                crop_height = min(
                    open_cv_image.shape[0] - crop_y,
                    int(h * head_ratio)
                )
                crop_x = max(0, int(x - w * 0.3))
                crop_width = min(
                    open_cv_image.shape[1] - crop_x,
                    int(w * shoulder_ratio)
                )
                
                # Crop image
                cropped = open_cv_image[
                    crop_y:crop_y + crop_height,
                    crop_x:crop_x + crop_width
                ]
                
                # Convert back to PIL
                cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(cropped_rgb)
        
        except Exception as e:
            # If face detection fails, use center crop
            width, height = image.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 3  # Bias towards top for head
            right = (width + min_dim) / 2
            bottom = top + min_dim
            
            image = image.crop((left, top, right, bottom))
        
        return image
    
    def enhance_image(self, image):
        """Enhance image quality"""
        
        from PIL import ImageEnhance
        
        # Adjust brightness and contrast
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image

class QualificationsProcessor(DocumentProcessor):
    """Qualifications document processor"""
    
    def __init__(self):
        super().__init__()
        self.allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    
    def process(self, file, user):
        """Process qualifications document"""
        
        # Extract text from document
        text = self.extract_text(file)
        
        # Parse qualifications
        qualifications = self.parse_qualifications(text)
        
        # Validate qualifications
        validated = self.validate_qualifications(qualifications)
        
        return {
            'original_text': text,
            'qualifications': qualifications,
            'validated': validated,
            'summary': self.generate_summary(qualifications)
        }
    
    def extract_text(self, file):
        """Extract text from qualifications document"""
        
        ext = os.path.splitext(file.name)[1].lower()
        text = ""
        
        if ext == '.pdf':
            # Extract from PDF
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        elif ext in ['.jpg', '.jpeg', '.png']:
            # Extract using OCR
            image = Image.open(file)
            text = pytesseract.image_to_string(image)
        
        return text.strip()
    
    def parse_qualifications(self, text):
        """Parse qualifications from text using AI"""
        
        # Use AI to parse qualifications
        # This is a simplified version
        qualifications = []
        
        # Look for common qualification patterns
        lines = text.split('\n')
        current_qual = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for qualification names
            qual_keywords = [
                'degree', 'diploma', 'certificate', 'certification',
                'bachelor', 'master', 'phd', 'doctorate',
                'matric', 'grade 12', 'nsc',
                'nqf', 'saqa'
            ]
            
            if any(keyword in line.lower() for keyword in qual_keywords):
                if current_qual:
                    qualifications.append(current_qual)
                    current_qual = {}
                
                current_qual['name'] = line
                current_qual['type'] = self.detect_qualification_type(line)
            
            # Look for institution
            elif 'university' in line.lower() or 'college' in line.lower() or 'school' in line.lower():
                current_qual['institution'] = line
            
            # Look for year
            elif any(year in line for year in ['201', '202', '200', '199']):
                current_qual['year'] = line
        
        if current_qual:
            qualifications.append(current_qual)
        
        return qualifications
    
    def detect_qualification_type(self, text):
        """Detect qualification type"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['phd', 'doctorate', 'd.phil']):
            return 'Doctorate'
        elif any(word in text_lower for word in ['master', 'masters', 'm.']):
            return 'Masters'
        elif any(word in text_lower for word in ['bachelor', 'b.', 'ba ', 'bsc', 'bcom']):
            return 'Bachelors'
        elif any(word in text_lower for word in ['diploma']):
            return 'Diploma'
        elif any(word in text_lower for word in ['certificate', 'certification']):
            return 'Certificate'
        elif any(word in text_lower for word in ['matric', 'grade 12', 'nsc']):
            return 'Matric'
        else:
            return 'Other'
    
    def validate_qualifications(self, qualifications):
        """Validate qualifications (placeholder for SAQA integration)"""
        # In production, integrate with SAQA database
        validated = []
        
        for qual in qualifications:
            qual['validated'] = True  # Simulated validation
            qual['validation_source'] = 'simulated'
            validated.append(qual)
        
        return validated
    
    def generate_summary(self, qualifications):
        """Generate qualifications summary"""
        
        if not qualifications:
            return "No qualifications found"
        
        highest_level = self.get_highest_level(qualifications)
        total_years = self.calculate_total_years(qualifications)
        
        summary = f"""
        Highest Qualification: {highest_level}
        Total Qualifications: {len(qualifications)}
        Estimated Study Years: {total_years}
        
        Qualifications:
        """
        
        for i, qual in enumerate(qualifications, 1):
            summary += f"{i}. {qual.get('name', 'Unknown')} - {qual.get('institution', 'Unknown')}\n"
        
        return summary
    
    def get_highest_level(self, qualifications):
        """Get highest qualification level"""
        
        level_order = {
            'Doctorate': 6,
            'Masters': 5,
            'Bachelors': 4,
            'Diploma': 3,
            'Certificate': 2,
            'Matric': 1,
            'Other': 0
        }
        
        highest = None
        highest_level = -1
        
        for qual in qualifications:
            level = level_order.get(qual.get('type', 'Other'), 0)
            if level > highest_level:
                highest_level = level
                highest = qual.get('name', 'Unknown')
        
        return highest or "Unknown"
    
    def calculate_total_years(self, qualifications):
        """Calculate total years of study"""
        
        # Estimate based on qualification types
        years_per_type = {
            'Doctorate': 4,
            'Masters': 2,
            'Bachelors': 3,
            'Diploma': 2,
            'Certificate': 1,
            'Matric': 1,
            'Other': 0
        }
        
        total_years = 0
        for qual in qualifications:
            total_years += years_per_type.get(qual.get('type', 'Other'), 0)
        
        return total_years
