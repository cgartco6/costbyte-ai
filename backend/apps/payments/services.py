"""
Payment services for South African payment methods
"""
import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
import requests
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

class PaymentProcessor:
    """Base payment processor"""
    
    def __init__(self):
        self.config = {}
    
    def initiate_payment(self, user, amount, metadata=None):
        """Initiate payment process"""
        raise NotImplementedError
    
    def verify_payment(self, reference):
        """Verify payment status"""
        raise NotImplementedError
    
    def process_webhook(self, request_data):
        """Process webhook notification"""
        raise NotImplementedError

class FNBProcessor(PaymentProcessor):
    """FNB Direct EFT Processor"""
    
    def __init__(self):
        super().__init__()
        self.config = {
            'account_number': settings.FNB_ACCOUNT_NUMBER,
            'account_name': settings.FNB_ACCOUNT_NAME,
            'branch_code': settings.FNB_BRANCH_CODE,
            'bank_name': 'First National Bank',
        }
    
    def initiate_payment(self, user, amount, metadata=None):
        """Generate FNB EFT payment details"""
        
        payment_details = {
            'bank_name': self.config['bank_name'],
            'account_name': self.config['account_name'],
            'account_number': self.config['account_number'],
            'branch_code': self.config['branch_code'],
            'branch_name': 'FNB Business Banking',
            'reference': metadata.get('merchant_reference') if metadata else '',
            'amount': str(amount),
            'currency': 'ZAR',
            'beneficiary': 'CostByte (Pty) Ltd',
            'payment_type': 'onceoff',
            'instructions': [
                f'Use reference: {metadata.get("merchant_reference") if metadata else ""}',
                'Payment must be exact amount',
                'Allow 2-3 hours for processing'
            ]
        }
        
        return {
            'type': 'bank_transfer',
            'details': payment_details,
            'payment_url': None,
            'qr_code_data': self.generate_qr_code(payment_details)
        }
    
    def generate_qr_code(self, payment_details):
        """Generate QR code for FNB app"""
        import qrcode
        import io
        import base64
        
        # Create FNB payment string
        payment_string = f"""
        Bank: {payment_details['bank_name']}
        Account: {payment_details['account_name']}
        Account No: {payment_details['account_number']}
        Branch: {payment_details['branch_code']}
        Amount: R{payment_details['amount']}
        Reference: {payment_details['reference']}
        """
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_payment(self, reference):
        """Verify FNB EFT payment (would integrate with FNB API)"""
        # In production, integrate with FNB Business Banking API
        # For now, simulate verification
        return {
            'verified': True,
            'amount': 500.00,
            'currency': 'ZAR',
            'timestamp': timezone.now().isoformat()
        }

class PayFastProcessor(PaymentProcessor):
    """PayFast payment processor"""
    
    def __init__(self):
        super().__init__()
        self.config = {
            'merchant_id': settings.PAYFAST_MERCHANT_ID,
            'merchant_key': settings.PAYFAST_MERCHANT_KEY,
            'passphrase': settings.PAYFAST_PASSPHRASE,
            'url': 'https://www.payfast.co.za/eng/process' if not settings.DEBUG else 'https://sandbox.payfast.co.za/eng/process'
        }
    
    def initiate_payment(self, user, amount, metadata=None):
        """Generate PayFast payment request"""
        
        data = {
            'merchant_id': self.config['merchant_id'],
            'merchant_key': self.config['merchant_key'],
            'return_url': f"{settings.FRONTEND_URL}/payment/success",
            'cancel_url': f"{settings.FRONTEND_URL}/payment/cancel",
            'notify_url': f"{settings.BACKEND_URL}/api/payments/payfast/webhook/",
            
            # Buyer details
            'name_first': user.first_name,
            'name_last': user.last_name,
            'email_address': user.email,
            'cell_number': user.phone_number,
            
            # Transaction details
            'm_payment_id': metadata.get('merchant_reference') if metadata else '',
            'amount': str(amount),
            'item_name': 'CostByte AI Job Application Service',
            'item_description': 'R500 once-off fee for AI-powered job application service',
            
            # Custom data
            'custom_str1': str(user.id),
            'custom_str2': user.sa_id_number,
            'custom_str3': 'CostByte Payment',
            
            # Security
            'signature': ''
        }
        
        # Generate signature
        signature = self.generate_signature(data)
        data['signature'] = signature
        
        return {
            'type': 'redirect',
            'payment_url': self.config['url'],
            'method': 'POST',
            'data': data
        }
    
    def generate_signature(self, data, passphrase=None):
        """Generate PayFast signature"""
        
        # Create parameter string
        param_string = ''
        for key in sorted(data.keys()):
            if key != 'signature' and data[key]:
                param_string += f"{key}={data[key].replace('&', '%26').replace('+', '%2B')}&"
        
        # Add passphrase if provided
        if passphrase:
            param_string += f"passphrase={passphrase}"
        else:
            param_string = param_string.rstrip('&')
        
        # Generate MD5 hash
        signature = hashlib.md5(param_string.encode()).hexdigest()
        return signature
    
    def verify_webhook(self, request_data):
        """Verify PayFast webhook signature"""
        # Get signature from request
        received_signature = request_data.get('signature')
        
        # Remove signature from data for verification
        verify_data = request_data.copy()
        if 'signature' in verify_data:
            del verify_data['signature']
        
        # Generate expected signature
        expected_signature = self.generate_signature(verify_data, self.config['passphrase'])
        
        return received_signature == expected_signature
    
    def process_webhook(self, request_data):
        """Process PayFast webhook"""
        
        if not self.verify_webhook(request_data):
            return {'error': 'Invalid signature'}, 400
        
        # Extract payment data
        payment_status = request_data.get('payment_status')
        merchant_reference = request_data.get('m_payment_id')
        
        return {
            'status': payment_status,
            'reference': merchant_reference,
            'data': request_data
        }

class PayShapProcessor(PaymentProcessor):
    """PayShap payment processor"""
    
    def initiate_payment(self, user, amount, metadata=None):
        """Generate PayShap payment request"""
        # PayShap integration would go here
        # This is a placeholder for actual implementation
        
        return {
            'type': 'redirect',
            'payment_url': f"https://payshap.example.com/pay?ref={metadata.get('merchant_reference') if metadata else ''}",
            'method': 'GET'
        }

class PaymentService:
    """Main payment service orchestrator"""
    
    PROCESSORS = {
        'fnb_eft': FNBProcessor,
        'payfast': PayFastProcessor,
        'payshap': PayShapProcessor,
    }
    
    @staticmethod
    def get_processor(method):
        """Get payment processor instance"""
        processor_class = PaymentService.PROCESSORS.get(method)
        if not processor_class:
            raise ValueError(f"Unsupported payment method: {method}")
        
        return processor_class()
    
    @staticmethod
    def initiate_payment(user, amount=500.00, method='payfast', metadata=None):
        """Initiate payment with selected method"""
        
        processor = PaymentService.get_processor(method)
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'user_id': str(user.id),
            'user_email': user.email,
            'timestamp': timezone.now().isoformat()
        })
        
        # Initiate payment
        result = processor.initiate_payment(user, amount, metadata)
        result['payment_method'] = method
        
        return result
    
    @staticmethod
    def distribute_revenue():
        """Distribute revenue according to specified percentages"""
        
        from .models import RevenueDistribution, BankAccount
        
        # Calculate weekly revenue
        last_week = timezone.now() - timezone.timedelta(days=7)
        from django.db.models import Sum
        from django.db.models.functions import TruncWeek
        
        # Get total revenue for the week
        # This would query actual payments
        # For now, simulate calculation
        
        weekly_revenue = Decimal('150000.00')  # Example amount
        
        # Get distribution percentages from bank accounts
        accounts = BankAccount.objects.filter(is_active=True)
        
        distribution = {
            'owner_fnb': Decimal('0.35'),   # 35%
            'african_bank': Decimal('0.15'), # 15%
            'ai_fnb': Decimal('0.20'),      # 20%
            'reserve_fnb': Decimal('0.20'), # 20%
            'growth_account': Decimal('0.10') # 10%
        }
        
        # Calculate amounts
        amounts = {}
        for account_type, percentage in distribution.items():
            amounts[account_type] = weekly_revenue * percentage
        
        # Create distribution record
        revenue_dist = RevenueDistribution.objects.create(
            distribution_date=timezone.now().date(),
            total_revenue=weekly_revenue,
            owner_amount=amounts['owner_fnb'],
            ai_amount=amounts['ai_fnb'],
            reserve_amount=amounts['reserve_fnb'],
            growth_amount=amounts['growth_account'],
            status='processing'
        )
        
        # Process transfers (simulated)
        # In production, integrate with bank APIs
        
        revenue_dist.status = 'completed'
        revenue_dist.processed_at = timezone.now()
        revenue_dist.save()
        
        # Update growth account with 10% weekly growth
        growth_account = BankAccount.objects.filter(
            account_type='reserve',
            name__icontains='growth'
        ).first()
        
        if growth_account:
            growth_amount = amounts['growth_account'] * Decimal('1.10')
            growth_account.current_balance += growth_amount
            growth_account.save()
        
        return revenue_dist
