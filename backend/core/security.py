# backend/core/security.py
from django.middleware.security import SecurityMiddleware
import cryptography
from cryptography.fernet import Fernet

class MilitaryGradeSecurity:
    
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
    def encrypt_data(self, data):
        """Encrypt sensitive data at rest"""
        return self.cipher.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data when needed"""
        return self.cipher.decrypt(encrypted_data).decode()
    
    def secure_file_upload(self, file):
        """Secure file upload with malware scanning"""
        # Scan for malware
        if self.scan_for_malware(file):
            raise SecurityException("Malware detected")
        
        # Encrypt file
        encrypted = self.encrypt_data(file.read())
        
        return encrypted
