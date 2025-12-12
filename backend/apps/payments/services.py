# backend/apps/payments/services.py
import requests
from django.conf import settings

class PaymentProcessor:
    """Handle multiple South African payment methods"""
    
    PAYMENT_METHODS = {
        'fnb_eft': FNBProcessor,
        'payfast': PayFastProcessor,
        'payshap': PayShapProcessor,
        'paystack': PayStackProcessor
    }
    
    def process_payment(self, user, amount=500.00, method='payfast'):
        processor = self.PAYMENT_METHODS.get(method)
        return processor().initiate_payment(user, amount)

class FNBProcessor:
    """Direct EFT to FNB account"""
    def initiate_payment(self, user, amount):
        # Generate unique payment reference
        reference = f"COSTBYTE-{user.id}-{uuid4().hex[:8]}"
        
        return {
            'bank': 'First National Bank',
            'account_number': settings.FNB_ACCOUNT_NUMBER,
            'branch_code': '250655',
            'reference': reference,
            'amount': amount,
            'beneficiary': 'CostByte (Pty) Ltd'
        }
