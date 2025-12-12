# backend/apps/users/models.py
from django.db import models
import re

class SouthAfricanUser(models.Model):
    """Model for verified South African users only"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    id_number = models.CharField(max_length=13, unique=True)
    sa_citizen = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True)
    verification_documents = models.JSONField(default=dict)
    
    def validate_sa_id(self, id_number):
        """Validate South African ID number"""
        if len(id_number) != 13 or not id_number.isdigit():
            return False
        
        # Luhn algorithm for SA ID validation
        total = 0
        for i in range(12):
            digit = int(id_number[i])
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(id_number[-1])
