"""
QR Code Utilities for ScanMe System (Enhanced Version)
Handles QR code generation and comprehensive processing with edge case handling
"""

import qrcode
from PIL import Image
import io
import base64
import os
import json
import re
from datetime import datetime

try:
    import numpy as np
except ImportError:
    np = None

def generate_user_qr_code(user_data, user_type='student', save_path=None, return_bytes=False):
    """
    Generate QR code for any user type (student, professor, admin)
    Args:
        user_data (dict): User information
        user_type (str): Type of user (student, professor, admin)
        save_path (str): Path to save QR code image
        return_bytes (bool): Return as bytes instead of saving
    Returns:
        str or bytes: File path or image bytes
    """
    try:
        # Create QR code data
        qr_data = create_qr_data(user_data, user_type)
        
        # Configure QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        if return_bytes:
            # Return as bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        
        if save_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            img.save(save_path)
            return save_path
        
        # Return as base64 string
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return img_base64
        
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return None

def generate_student_qr_code(student_data, save_path=None, return_bytes=False):
    """
    Generate QR code for student (backward compatibility)
    Args:
        student_data (dict): Student information
        save_path (str): Path to save QR code image
        return_bytes (bool): Return as bytes instead of saving
    Returns:
        str or bytes: File path or image bytes
    """
    return generate_user_qr_code(student_data, 'student', save_path, return_bytes)

def create_qr_data(user_data, user_type='student'):
    """
    Create standardized QR code data format for any user type
    Args:
        user_data (dict): User information
        user_type (str): Type of user (student, professor, admin)
    Returns:
        str: JSON formatted QR code data
    """
    if user_type == 'student':
        qr_payload = {
            'type': 'student_attendance',
            'student_id': user_data.get('id'),
            'student_no': user_data.get('student_no'),
            'name': user_data.get('name'),
            'department': user_data.get('department'),
            'section': user_data.get('section'),
            'year_level': user_data.get('year_level'),
            'generated_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
    else:
        # For professors and admins
        qr_payload = {
            'type': f'{user_type}_identification',
            'user_id': user_data.get('id'),
            'username': user_data.get('username'),
            'email': user_data.get('email'),
            'role': user_data.get('role'),
            'name': user_data.get('display_name', user_data.get('username')),
            'generated_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
    
    return json.dumps(qr_payload, separators=(',', ':'))

def validate_qr_data(qr_content):
    """
    Comprehensive QR code content validation with edge case handling
    Args:
        qr_content (str): Raw QR code content
    Returns:
        dict: Validation result with parsed data
    """
    # Edge Case 1: Empty QR Code
    if not qr_content:
        return {
            'valid': False,
            'error': 'QR code is empty',
            'error_code': 'EMPTY_QR',
            'data': None
        }
    
    # Edge Case 2: Whitespace-only data
    if not qr_content.strip():
        return {
            'valid': False,
            'error': 'QR code contains only whitespace',
            'error_code': 'WHITESPACE_ONLY',
            'data': None
        }
    
    # Edge Case 3: Extremely long data (potential DoS)
    if len(qr_content) > 5000:  # Reasonable limit for QR codes
        return {
            'valid': False,
            'error': 'QR code data exceeds maximum length (5000 characters)',
            'error_code': 'DATA_TOO_LONG',
            'data': None
        }
    
    # Edge Case 4: Binary data detection
    try:
        qr_content.encode('utf-8')
    except UnicodeEncodeError:
        return {
            'valid': False,
            'error': 'QR code contains invalid binary data',
            'error_code': 'BINARY_DATA',
            'data': None
        }
    
    # Clean the content
    cleaned_content = qr_content.strip()
    
    # Edge Case 5: HTML/Script injection detection
    dangerous_patterns = [
        '<script', '</script>', '<iframe', '<object', '<embed',
        'javascript:', 'vbscript:', 'onload=', 'onerror=', 'onclick='
    ]
    
    content_lower = cleaned_content.lower()
    for pattern in dangerous_patterns:
        if pattern in content_lower:
            return {
                'valid': False,
                'error': f'QR code contains potentially malicious content: {pattern}',
                'error_code': 'MALICIOUS_CONTENT',
                'data': None
            }
    
    # Edge Case 6: SQL injection pattern detection
    sql_patterns = [
        "'; drop table", "'; delete from", "union select", 
        "' or '1'='1", "' or 1=1", "--", "/*", "*/"
    ]
    
    for pattern in sql_patterns:
        if pattern in content_lower:
            return {
                'valid': False,
                'error': f'QR code contains potential SQL injection pattern: {pattern}',
                'error_code': 'SQL_INJECTION',
                'data': None
            }
    
    try:
        # Try to parse as JSON
        data = json.loads(cleaned_content)
        
        # Edge Case 7: Invalid data types in JSON
        if not isinstance(data, dict):
            return {
                'valid': False,
                'error': 'QR code JSON must be an object/dictionary',
                'error_code': 'INVALID_JSON_TYPE',
                'data': None
            }
        
        # Edge Case 8: Null/undefined values in required fields
        for key, value in data.items():
            if value is None:
                return {
                    'valid': False,
                    'error': f'Field "{key}" cannot be null',
                    'error_code': 'NULL_VALUE',
                    'data': None
                }
        
        # Validate required fields for student attendance
        if data.get('type') == 'student_attendance':
            required_fields = ['type', 'student_id', 'student_no', 'name']
            missing_fields = [field for field in required_fields if field not in data or data[field] == '']
            
            if missing_fields:
                return {
                    'valid': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'error_code': 'MISSING_FIELDS',
                    'data': None
                }
            
            # Edge Case 9: Invalid data types for specific fields
            if not isinstance(data.get('student_id'), (int, str)):
                return {
                    'valid': False,
                    'error': 'student_id must be a number or string',
                    'error_code': 'INVALID_STUDENT_ID_TYPE',
                    'data': None
                }
            
            # Try to convert student_id to integer if it's a string number
            try:
                student_id = data['student_id']
                if isinstance(student_id, str):
                    # Check if string contains only digits or is a valid number
                    if student_id.isdigit():
                        data['student_id'] = int(student_id)
                    else:
                        # Check if it's a valid student ID format (could contain letters)
                        if not student_id.replace('-', '').replace('_', '').isalnum():
                            return {
                                'valid': False,
                                'error': 'student_id contains invalid characters',
                                'error_code': 'INVALID_STUDENT_ID_FORMAT',
                                'data': None
                            }
            except (ValueError, TypeError):
                return {
                    'valid': False,
                    'error': 'student_id format is invalid',
                    'error_code': 'INVALID_STUDENT_ID_FORMAT',
                    'data': None
                }
            
            # Validate student_no format
            student_no = str(data.get('student_no', '')).strip()
            if not student_no or len(student_no) > 20:
                return {
                    'valid': False,
                    'error': 'student_no must be 1-20 characters',
                    'error_code': 'INVALID_STUDENT_NO',
                    'data': None
                }
            
            # Validate name
            name = str(data.get('name', '')).strip()
            if not name or len(name) > 100:
                return {
                    'valid': False,
                    'error': 'name must be 1-100 characters',
                    'error_code': 'INVALID_NAME',
                    'data': None
                }
            
            # Sanitize Unicode characters
            try:
                data['name'] = name.encode('utf-8').decode('utf-8')
                data['student_no'] = student_no.encode('utf-8').decode('utf-8')
            except UnicodeError:
                return {
                    'valid': False,
                    'error': 'Invalid Unicode characters in student data',
                    'error_code': 'UNICODE_ERROR',
                    'data': None
                }
        
        # Validate type
        valid_types = ['student_attendance', 'professor_identification', 'admin_identification']
        if data.get('type') not in valid_types:
            return {
                'valid': False,
                'error': f'Invalid QR code type. Must be one of: {", ".join(valid_types)}',
                'error_code': 'INVALID_TYPE',
                'data': None
            }
        
        return {
            'valid': True,
            'data': data,
            'error': None,
            'error_code': None
        }
        
    except json.JSONDecodeError as e:
        # Edge Case 10: Malformed JSON
        if '{' in cleaned_content or '[' in cleaned_content:
            return {
                'valid': False,
                'error': f'Malformed JSON in QR code: {str(e)}',
                'error_code': 'MALFORMED_JSON',
                'data': None
            }
        
        # Try legacy format (just student number) or SCANME_ format
        if cleaned_content and len(cleaned_content.strip()) > 0:
            # Check if it's SCANME_ format (our QR code format)
            if cleaned_content.startswith('SCANME_'):
                # This is our QR code format - extract the hash and treat as QR data
                return {
                    'valid': True,
                    'data': {
                        'type': 'scanme_qr_code',
                        'qr_data': cleaned_content,
                        'legacy': False
                    },
                    'error': None,
                    'error_code': None
                }
            
            # Validate legacy format (plain student number)
            if len(cleaned_content) > 20:
                return {
                    'valid': False,
                    'error': 'Legacy student number too long (max 20 characters)',
                    'error_code': 'LEGACY_TOO_LONG',
                    'data': None
                }
            
            # Check for invalid characters in student number
            if not cleaned_content.replace('-', '').replace('_', '').isalnum():
                return {
                    'valid': False,
                    'error': 'Legacy student number contains invalid characters',
                    'error_code': 'LEGACY_INVALID_CHARS',
                    'data': None
                }
            
            return {
                'valid': True,
                'data': {
                    'type': 'legacy_student_no',
                    'student_no': cleaned_content,
                    'legacy': True
                },
                'error': None,
                'error_code': None
            }
        
        return {
            'valid': False,
            'error': 'Invalid QR code format - not JSON and not valid legacy format',
            'error_code': 'INVALID_FORMAT',
            'data': None
        }

def generate_bulk_qr_codes(students_list, output_dir):
    """
    Generate QR codes for multiple students
    Args:
        students_list (list): List of student dictionaries
        output_dir (str): Directory to save QR code images
    Returns:
        dict: Generation results with success/failure counts
    """
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    for student in students_list:
        try:
            filename = f"{student.get('student_no', 'unknown')}_qr.png"
            filepath = os.path.join(output_dir, filename)
            
            success = generate_student_qr_code(student, save_path=filepath)
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to generate QR for {student.get('name', 'Unknown')}")
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Error processing {student.get('name', 'Unknown')}: {str(e)}")
    
    return results

def create_qr_code_with_info(student_data, include_photo=False, size=(300, 400)):
    """
    Create QR code with student information overlay
    Args:
        student_data (dict): Student information
        include_photo (bool): Include student photo if available
        size (tuple): Image size (width, height)
    Returns:
        PIL.Image: Combined QR code and info image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Generate QR code
        qr_img_bytes = generate_student_qr_code(student_data, return_bytes=True)
        if not qr_img_bytes:
            return None
        
        qr_img = Image.open(io.BytesIO(qr_img_bytes))
        
        # Create canvas
        canvas = Image.new('RGB', size, 'white')
        draw = ImageDraw.Draw(canvas)
        
        # Calculate positions
        qr_size = 200
        qr_img = qr_img.resize((qr_size, qr_size))
        qr_x = (size[0] - qr_size) // 2
        qr_y = 50
        
        # Paste QR code
        canvas.paste(qr_img, (qr_x, qr_y))
        
        # Add student information
        info_y = qr_y + qr_size + 20
        
        try:
            # Try to use a better font
            font_large = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            # Fall back to default font
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw student info
        info_lines = [
            f"Name: {student_data.get('name', 'N/A')}",
            f"Student No: {student_data.get('student_no', 'N/A')}",
            f"Department: {student_data.get('department', 'N/A')}",
            f"Section: {student_data.get('section', 'N/A')}",
            f"Year: {student_data.get('year_level', 'N/A')}"
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = info_y + (i * 20)
            # Center text
            bbox = draw.textbbox((0, 0), line, font=font_small)
            text_width = bbox[2] - bbox[0]
            x_pos = (size[0] - text_width) // 2
            draw.text((x_pos, y_pos), line, fill='black', font=font_small)
        
        return canvas
        
    except Exception as e:
        print(f"Error creating QR code with info: {str(e)}")
        return None

# Placeholder functions for camera scanning (to be implemented when libraries are available)
def scan_qr_from_camera():
    """
    Placeholder for camera-based QR scanning
    Requires opencv-python and pyzbar packages
    """
    return {
        'success': False,
        'error': 'Camera scanning not available. Install opencv-python and pyzbar packages.',
        'data': None
    }

def scan_qr_from_image(image_path):
    """
    Placeholder for image-based QR scanning
    Requires opencv-python and pyzbar packages
    """
    return {
        'success': False,
        'error': 'Image scanning not available. Install opencv-python and pyzbar packages.',
        'data': None
    }

def process_uploaded_qr_image(uploaded_file):
    """
    Process uploaded QR code image with comprehensive edge case handling
    Args:
        uploaded_file: Flask uploaded file object
    Returns:
        dict: Processing result
    """
    try:
        # Edge Case 1: No file uploaded
        if not uploaded_file:
            return {
                'success': False,
                'error': 'No file uploaded',
                'error_code': 'NO_FILE',
                'data': None
            }
        
        # Edge Case 2: Empty filename
        if not uploaded_file.filename or uploaded_file.filename == '':
            return {
                'success': False,
                'error': 'No file selected',
                'error_code': 'EMPTY_FILENAME',
                'data': None
            }
        
        # Edge Case 3: File size validation
        uploaded_file.seek(0, 2)  # Seek to end to get file size
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)  # Reset to beginning
        
        # Max file size: 10MB
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            return {
                'success': False,
                'error': f'File too large. Maximum size is {max_size / (1024*1024):.1f}MB',
                'error_code': 'FILE_TOO_LARGE',
                'data': None
            }
        
        if file_size == 0:
            return {
                'success': False,
                'error': 'Uploaded file is empty',
                'error_code': 'EMPTY_FILE',
                'data': None
            }
        
        # Edge Case 4: File format validation
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        file_extension = os.path.splitext(uploaded_file.filename.lower())[1]
        
        if file_extension not in allowed_extensions:
            return {
                'success': False,
                'error': f'Invalid file format. Allowed formats: {", ".join(allowed_extensions)}',
                'error_code': 'INVALID_FORMAT',
                'data': None
            }
        
        # Edge Case 5: Read and validate file content
        try:
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset for potential re-reading
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read uploaded file: {str(e)}',
                'error_code': 'READ_ERROR',
                'data': None
            }
        
        # Edge Case 6: Validate image content
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(file_content))
            
            # Validate image dimensions
            width, height = image.size
            if width < 50 or height < 50:
                return {
                    'success': False,
                    'error': 'Image too small. Minimum size is 50x50 pixels',
                    'error_code': 'IMAGE_TOO_SMALL',
                    'data': None
                }
            
            if width > 5000 or height > 5000:
                return {
                    'success': False,
                    'error': 'Image too large. Maximum size is 5000x5000 pixels',
                    'error_code': 'IMAGE_TOO_LARGE',
                    'data': None
                }
            
            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid or corrupted image file: {str(e)}',
                'error_code': 'CORRUPTED_IMAGE',
                'data': None
            }
        
        # Edge Case 7: Check if image scanning libraries are available
        try:
            import cv2
            import pyzbar.pyzbar as pyzbar
        except ImportError as e:
            return {
                'success': False,
                'error': 'QR image processing requires opencv-python and pyzbar packages. Please install them or enter QR data manually.',
                'error_code': 'MISSING_LIBRARIES',
                'data': None,
                'install_hint': 'Run: pip install opencv-python pyzbar'
            }
        
        # Edge Case 8: Process image for QR codes
        try:
            # Convert PIL image to OpenCV format
            if np is None:
                return {
                    'success': False,
                    'error': 'NumPy is required for image processing. Please install: pip install numpy',
                    'error_code': 'MISSING_NUMPY',
                    'data': None
                }
                
            image_array = np.array(image)
            if len(image_array.shape) == 3:
                image_cv = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            else:
                image_cv = image_array
            
            # Decode QR codes
            qr_codes = pyzbar.decode(image_cv)
            
            # Edge Case 9: No QR code found
            if not qr_codes:
                return {
                    'success': False,
                    'error': 'No QR code found in the uploaded image',
                    'error_code': 'NO_QR_FOUND',
                    'data': None,
                    'hint': 'Make sure the QR code is clearly visible and not distorted'
                }
            
            # Edge Case 10: Multiple QR codes found
            if len(qr_codes) > 1:
                return {
                    'success': False,
                    'error': f'Multiple QR codes found in image ({len(qr_codes)}). Please upload an image with only one QR code.',
                    'error_code': 'MULTIPLE_QR_CODES',
                    'data': None
                }
            
            # Extract QR code data
            qr_code = qr_codes[0]
            qr_data = qr_code.data.decode('utf-8')
            
            # Edge Case 11: Empty QR code data
            if not qr_data:
                return {
                    'success': False,
                    'error': 'QR code found but contains no data',
                    'error_code': 'EMPTY_QR_DATA',
                    'data': None
                }
            
            # Validate the extracted QR data using existing validation
            validation_result = validate_qr_data(qr_data)
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f'Invalid QR code content: {validation_result["error"]}',
                    'error_code': validation_result.get('error_code', 'VALIDATION_FAILED'),
                    'data': None
                }
            
            return {
                'success': True,
                'error': None,
                'error_code': None,
                'data': validation_result['data'],
                'raw_data': qr_data,
                'qr_type': qr_code.type,
                'qr_rect': {
                    'x': qr_code.rect.left,
                    'y': qr_code.rect.top,
                    'width': qr_code.rect.width,
                    'height': qr_code.rect.height
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing QR code from image: {str(e)}',
                'error_code': 'PROCESSING_ERROR',
                'data': None
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error processing uploaded image: {str(e)}',
            'error_code': 'UNEXPECTED_ERROR',
            'data': None
        }

def get_qr_scanner_status():
    """
    Check if QR scanning libraries are available
    Returns:
        dict: Scanner status information
    """
    status = {
        'qr_generation': True,  # Always available with qrcode package
        'camera_scanning': False,
        'image_scanning': False,
        'missing_packages': []
    }
    
    try:
        import cv2
        status['camera_scanning'] = True
        status['image_scanning'] = True
    except ImportError:
        status['missing_packages'].append('opencv-python')
    
    try:
        import pyzbar
    except ImportError:
        status['missing_packages'].append('pyzbar')
        status['camera_scanning'] = False
        status['image_scanning'] = False
    
    return status