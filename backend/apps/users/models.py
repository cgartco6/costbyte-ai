from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid

class User(AbstractUser):
    """Custom user model for South African citizens only"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # South African ID Number (13 digits)
    sa_id_number = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{13}$',
                message='South African ID must be 13 digits'
            )
        ],
        help_text="13-digit South African ID number"
    )
    
    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^(\+27|0)[1-9][0-9]{8}$',
                message='Enter a valid South African phone number'
            )
        ]
    )
    whatsapp_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="WhatsApp number for notifications"
    )
    
    # Verification Status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_method = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Manual Verification'),
            ('auto', 'Auto Verification'),
            ('pending', 'Pending')
        ],
        default='pending'
    )
    
    # Payment Status
    has_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00
    )
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Profile Information
    current_occupation = models.CharField(max_length=255, blank=True, null=True)
    years_experience = models.IntegerField(default=0)
    highest_qualification = models.CharField(max_length=255, blank=True, null=True)
    preferred_industries = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    salary_expectation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # AI Settings
    ai_settings = models.JSONField(default=dict, blank=True)
    daily_application_limit = models.IntegerField(default=10)
    
    # Statistics
    total_applications = models.IntegerField(default=0)
    successful_applications = models.IntegerField(default=0)
    interview_invites = models.IntegerField(default=0)
    job_offers = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Security
    mfa_enabled = models.BooleanField(default=False)
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['sa_id_number']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['has_paid']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.sa_id_number})"
    
    def verify_sa_id(self):
        """Validate South African ID number using Luhn algorithm"""
        from .validators import validate_sa_id_number
        return validate_sa_id_number(self.sa_id_number)
    
    def calculate_age(self):
        """Calculate age from SA ID number"""
        from datetime import datetime
        id_str = str(self.sa_id_number)
        year = int(id_str[0:2])
        month = int(id_str[2:4])
        day = int(id_str[4:6])
        
        # Determine century
        current_year = datetime.now().year % 100
        century = 2000 if year <= current_year else 1900
        birth_year = century + year
        
        birth_date = datetime(birth_year, month, day)
        age = datetime.now().year - birth_date.year
        
        if (datetime.now().month, datetime.now().day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    def can_apply(self):
        """Check if user can submit more applications today"""
        from django.db.models import Count
        from django.utils import timezone
        
        today = timezone.now().date()
        today_applications = self.jobapplication_set.filter(
            created_at__date=today
        ).count()
        
        return today_applications < self.daily_application_limit
    
    @property
    def is_south_african(self):
        """Verify if user is South African citizen"""
        return self.is_verified and self.verify_sa_id()

class UserProfile(models.Model):
    """Extended profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        blank=True,
        null=True
    )
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    disability_status = models.BooleanField(default=False)
    disability_details = models.TextField(blank=True, null=True)
    
    # Address
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Career Preferences
    career_level = models.CharField(
        max_length=50,
        choices=[
            ('entry', 'Entry Level'),
            ('mid', 'Mid Level'),
            ('senior', 'Senior Level'),
            ('executive', 'Executive')
        ],
        default='mid'
    )
    job_types = models.JSONField(default=list, blank=True)  # full-time, part-time, etc.
    work_preference = models.JSONField(default=list, blank=True)  # remote, hybrid, onsite
    
    # Skills
    skills = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    
    # Social Profiles
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    
    # Consent
    marketing_consent = models.BooleanField(default=False)
    data_sharing_consent = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.get_full_name()}"

class LoginHistory(models.Model):
    """Track user login history for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.JSONField(null=True, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = 'Login Histories'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time} - {'Success' if self.success else 'Failed'}"
