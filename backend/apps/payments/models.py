from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone

class Payment(models.Model):
    """Payment model for R500 once-off fee"""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('fnb_eft', 'FNB Direct EFT'),
        ('payfast', 'PayFast'),
        ('payshap', 'PayShap'),
        ('paystack', 'PayStack'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    currency = models.CharField(max_length=3, default='ZAR')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Reference Numbers
    merchant_reference = models.CharField(max_length=100, unique=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    bank_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    status_message = models.TextField(blank=True, null=True)
    
    # Payment Provider Data
    provider_data = models.JSONField(default=dict, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Webhook
    webhook_received = models.BooleanField(default=False)
    webhook_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant_reference']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.merchant_reference} - {self.user.username} - {self.amount} {self.currency}"
    
    def mark_as_completed(self, reference=None):
        """Mark payment as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if reference:
            self.payment_reference = reference
        self.save()
        
        # Update user payment status
        self.user.has_paid = True
        self.user.payment_date = timezone.now()
        self.user.payment_reference = self.merchant_reference
        self.user.save()
    
    def generate_merchant_reference(self):
        """Generate unique merchant reference"""
        import random
        import string
        
        if not self.merchant_reference:
            prefix = "COSTBYTE"
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.merchant_reference = f"{prefix}-{timestamp}-{random_str}"
        
        return self.merchant_reference
    
    def save(self, *args, **kwargs):
        if not self.merchant_reference:
            self.generate_merchant_reference()
        super().save(*args, **kwargs)

class PaymentMethod(models.Model):
    """Available payment methods"""
    
    PAYMENT_TYPES = [
        ('bank', 'Bank Transfer'),
        ('card', 'Card Payment'),
        ('wallet', 'Digital Wallet'),
        ('ussd', 'USSD'),
    ]
    
    name = models.CharField(max_length=50)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    provider = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    processing_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    processing_fee_type = models.CharField(
        max_length=10,
        choices=[('fixed', 'Fixed'), ('percentage', 'Percentage')],
        default='fixed'
    )
    
    # Configuration
    config = models.JSONField(default=dict, blank=True)
    
    # Display
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.provider})"

class BankAccount(models.Model):
    """Bank accounts for revenue distribution"""
    
    BANK_NAMES = [
        ('fnb', 'First National Bank'),
        ('absa', 'Absa Bank'),
        ('standard', 'Standard Bank'),
        ('nedbank', 'Nedbank'),
        ('capitec', 'Capitec Bank'),
        ('african_bank', 'African Bank'),
    ]
    
    ACCOUNT_TYPES = [
        ('owner', 'Owner Account'),
        ('ai', 'AI Development Account'),
        ('reserve', 'Reserve Account'),
        ('operational', 'Operational Account'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    bank_name = models.CharField(max_length=50, choices=BANK_NAMES)
    account_number = models.CharField(max_length=20)
    branch_code = models.CharField(max_length=20)
    account_holder = models.CharField(max_length=200)
    
    # Distribution percentage
    distribution_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of revenue to distribute to this account"
    )
    
    # Balance tracking
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    last_reconciled = models.DateTimeField(null=True, blank=True)
    
    # Security
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['account_type', 'bank_name']
    
    def __str__(self):
        return f"{self.account_type} - {self.bank_name} ({self.account_number})"

class RevenueDistribution(models.Model):
    """Track revenue distributions"""
    
    distribution_date = models.DateField()
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Distribution amounts
    owner_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    ai_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    reserve_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    growth_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    # Transaction references
    owner_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    ai_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    reserve_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-distribution_date']
    
    def __str__(self):
        return f"Revenue Distribution - {self.distribution_date}"
