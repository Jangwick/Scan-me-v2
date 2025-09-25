"""
QR Code Utilities for ScanMe System (Simplified Version)
Handles QR code generation and basic processing
Note: Camera scanning features require additional setup
"""

import qrcode
from PIL import Image
import io
import base64
import os
import json
from datetime import datetime

def generate_student_qr_code(student_data, save_path=None, return_bytes=False):
    """
    Generate QR code for student
    Args:
        student_data (dict): Student information
        save_path (str): Path to save QR code image
        return_bytes (bool): Return as bytes instead of saving
    Returns:
        str or bytes: File path or image bytes
    """
    try:
        # Create QR code data
        qr_data = create_qr_data(student_data)
        
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

def create_qr_data(student_data):
    """
    Create standardized QR code data format
    Args:
        student_data (dict): Student information
    Returns:
        str: JSON formatted QR code data
    """
    qr_payload = {
        'type': 'student_attendance',
        'student_id': student_data.get('id'),
        'student_no': student_data.get('student_no'),
        'name': student_data.get('name'),
        'department': student_data.get('department'),
        'section': student_data.get('section'),
        'year_level': student_data.get('year_level'),
        'generated_at': datetime.utcnow().isoformat(),
        'version': '1.0'
    }
    
    return json.dumps(qr_payload, separators=(',', ':'))

def validate_qr_data(qr_content):
    """
    Validate QR code content format
    Args:
        qr_content (str): Raw QR code content
    Returns:
        dict: Validation result with parsed data
    """
    try:
        # Try to parse as JSON
        data = json.loads(qr_content)
        
        # Validate required fields
        required_fields = ['type', 'student_id', 'student_no', 'name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                'valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'data': None
            }
        
        # Validate type
        if data.get('type') != 'student_attendance':
            return {
                'valid': False,
                'error': 'Invalid QR code type',
                'data': None
            }
        
        return {
            'valid': True,
            'data': data,
            'error': None
        }
        
    except json.JSONDecodeError:
        # Try legacy format (just student number)
        if qr_content and len(qr_content.strip()) > 0:
            return {
                'valid': True,
                'data': {
                    'type': 'legacy_student_no',
                    'student_no': qr_content.strip(),
                    'legacy': True
                },
                'error': None
            }
        
        return {
            'valid': False,
            'error': 'Invalid QR code format',
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
    Process uploaded QR code image
    Args:
        uploaded_file: Flask uploaded file object
    Returns:
        dict: Processing result
    """
    try:
        # For now, return a placeholder response
        # This would normally scan the uploaded image for QR codes
        return {
            'success': False,
            'error': 'QR image processing requires opencv-python and pyzbar packages. Please enter QR data manually.',
            'data': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing image: {str(e)}',
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