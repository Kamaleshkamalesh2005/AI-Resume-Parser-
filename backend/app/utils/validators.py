"""
Input Validation Module
Validates file uploads, file formats, and data integrity
"""

import regex as re
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)


def is_allowed_file(filename, allowed_extensions):
    """
    Validate if uploaded file has allowed extension
    
    Args:
        filename (str): Name of the file
        allowed_extensions (set): Allowed file extensions
    
    Returns:
        bool: True if file is allowed, False otherwise
    """
    if not filename:
        return False
    
    # Extract file extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in allowed_extensions


def validate_file_upload(file, allowed_extensions):
    """
    Comprehensive file validation
    
    Args:
        file: FileStorage object from Flask request
        allowed_extensions (set): Allowed file extensions
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if file exists
    if not file or file.filename == '':
        return False, 'No file selected'
    
    # Check file extension
    if not is_allowed_file(file.filename, allowed_extensions):
        return False, f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'
    
    # Validate filename safety
    try:
        secure_name = secure_filename(file.filename)
        if not secure_name:
            return False, 'Invalid filename'
    except Exception as e:
        logger.error(f"Filename validation error: {str(e)}")
        return False, 'Filename validation failed'
    
    return True, None


def extract_email(text):
    """
    Extract email addresses using regex
    Email pattern: username@domain.extension
    
    Args:
        text (str): Text to search for emails
    
    Returns:
        list: List of found email addresses
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return emails


def extract_phone(text):
    """
    Extract phone numbers using regex
    Supports multiple formats: (123)456-7890, 123-456-7890, 123.456.7890, etc.
    
    Args:
        text (str): Text to search for phone numbers
    
    Returns:
        list: List of found phone numbers
    """
    # Flexible phone pattern
    phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
    phones = re.findall(phone_pattern, text)
    
    # Format results
    formatted_phones = []
    for match in phones:
        phone = ''.join([m for m in match if m])
        formatted_phones.append(phone)
    
    return formatted_phones


def validate_text_length(text, min_length=0, max_length=1000000):
    """
    Validate text length constraints
    
    Args:
        text (str): Text to validate
        min_length (int): Minimum allowed length
        max_length (int): Maximum allowed length
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(text) < min_length:
        return False, f'Text is too short (minimum {min_length} characters)'
    
    if len(text) > max_length:
        return False, f'Text exceeds maximum length ({max_length} characters)'
    
    return True, None
