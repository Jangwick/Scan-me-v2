"""
QR Code Utilities for ScanMe System
Handles QR code generation, scanning, and processing
"""

import qrcode
import cv2
from pyzbar import pyzbar
from PIL import Image
import numpy as np
import os
import io
import base64
from datetime import datetime, timedelta

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
            # Save to file
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            img.save(save_path)
            return save_path
        
        return img
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def create_qr_data(student_data):
    """
    Create standardized QR code data string
    Args:
        student_data (dict): Student information
    Returns:
        str: Formatted QR data string
    """
    # Format: SCANME|STUDENT_ID|STUDENT_NO|TIMESTAMP
    timestamp = int(datetime.utcnow().timestamp())
    
    qr_data = f"SCANME|{student_data.get('id', '')}|{student_data.get('student_no', '')}|{timestamp}"
    
    return qr_data

def decode_qr_data(qr_data):
    """
    Decode QR code data string
    Args:
        qr_data (str): QR code data string
    Returns:
        dict: Decoded data or None if invalid
    """
    try:
        if not qr_data.startswith('SCANME|'):
            return None
        
        parts = qr_data.split('|')
        if len(parts) != 4:
            return None
        
        return {
            'prefix': parts[0],
            'student_id': parts[1],
            'student_no': parts[2],
            'timestamp': int(parts[3])
        }
        
    except Exception as e:
        print(f"Error decoding QR data: {e}")
        return None

def scan_qr_from_image(image_data):
    """
    Scan QR code from image data
    Args:
        image_data: Image data (file path, bytes, or numpy array)
    Returns:
        list: List of decoded QR codes
    """
    try:
        # Handle different input types
        if isinstance(image_data, str):
            # File path
            image = cv2.imread(image_data)
        elif isinstance(image_data, bytes):
            # Bytes data
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            # Assume numpy array
            image = image_data
        
        if image is None:
            return []
        
        # Convert to grayscale for better detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Decode QR codes
        qr_codes = pyzbar.decode(gray)
        
        results = []
        for qr_code in qr_codes:
            # Extract QR code data
            qr_data = qr_code.data.decode('utf-8')
            qr_type = qr_code.type
            
            # Get bounding box coordinates
            points = qr_code.polygon
            if len(points) == 4:
                x_coords = [p.x for p in points]
                y_coords = [p.y for p in points]
                bbox = {
                    'x': min(x_coords),
                    'y': min(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords)
                }
            else:
                bbox = None
            
            results.append({
                'data': qr_data,
                'type': qr_type,
                'bbox': bbox,
                'decoded_data': decode_qr_data(qr_data)
            })
        
        return results
        
    except Exception as e:
        print(f"Error scanning QR code from image: {e}")
        return []

def scan_qr_from_webcam(duration=10):
    """
    Scan QR codes from webcam feed
    Args:
        duration (int): Duration to scan in seconds
    Returns:
        list: List of scanned QR codes
    """
    try:
        cap = cv2.VideoCapture(0)
        scanned_codes = []
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < duration:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Scan for QR codes in current frame
            qr_results = scan_qr_from_image(frame)
            
            for result in qr_results:
                qr_data = result['data']
                if qr_data not in [code['data'] for code in scanned_codes]:
                    scanned_codes.append(result)
                    print(f"QR Code detected: {qr_data}")
            
            # Display frame (optional)
            cv2.imshow('QR Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        return scanned_codes
        
    except Exception as e:
        print(f"Error scanning from webcam: {e}")
        return []

def validate_qr_code(qr_data):
    """
    Validate QR code format and content
    Args:
        qr_data (str): QR code data
    Returns:
        dict: Validation result
    """
    result = {
        'valid': False,
        'error': None,
        'decoded_data': None
    }
    
    try:
        # Decode QR data
        decoded = decode_qr_data(qr_data)
        
        if not decoded:
            result['error'] = 'Invalid QR code format'
            return result
        
        # Check if QR code is too old (e.g., older than 1 year)
        qr_timestamp = datetime.fromtimestamp(decoded['timestamp'])
        if datetime.utcnow() - qr_timestamp > timedelta(days=365):
            result['error'] = 'QR code has expired'
            return result
        
        result['valid'] = True
        result['decoded_data'] = decoded
        
    except Exception as e:
        result['error'] = f'Error validating QR code: {str(e)}'
    
    return result

def create_qr_code_batch(students_data, output_dir):
    """
    Generate QR codes for multiple students
    Args:
        students_data (list): List of student data dictionaries
        output_dir (str): Output directory for QR codes
    Returns:
        dict: Results summary
    """
    results = {
        'success': [],
        'failed': [],
        'total': len(students_data)
    }
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    for student in students_data:
        try:
            filename = f"qr_{student.get('student_no', student.get('id', 'unknown'))}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Generate QR code
            generated_path = generate_student_qr_code(student, filepath)
            
            if generated_path:
                results['success'].append({
                    'student_no': student.get('student_no'),
                    'name': f"{student.get('first_name', '')} {student.get('last_name', '')}",
                    'filepath': generated_path
                })
            else:
                results['failed'].append({
                    'student_no': student.get('student_no'),
                    'error': 'Failed to generate QR code'
                })
                
        except Exception as e:
            results['failed'].append({
                'student_no': student.get('student_no'),
                'error': str(e)
            })
    
    return results

def qr_code_to_base64(qr_image):
    """
    Convert QR code image to base64 string
    Args:
        qr_image: PIL Image or file path
    Returns:
        str: Base64 encoded image string
    """
    try:
        if isinstance(qr_image, str):
            # File path
            with open(qr_image, 'rb') as img_file:
                img_data = img_file.read()
        else:
            # PIL Image
            img_byte_arr = io.BytesIO()
            qr_image.save(img_byte_arr, format='PNG')
            img_data = img_byte_arr.getvalue()
        
        # Encode to base64
        base64_string = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/png;base64,{base64_string}"
        
    except Exception as e:
        print(f"Error converting QR code to base64: {e}")
        return None

def enhance_image_for_scanning(image):
    """
    Enhance image quality for better QR code scanning
    Args:
        image: OpenCV image
    Returns:
        numpy.ndarray: Enhanced image
    """
    try:
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply histogram equalization
        enhanced = cv2.equalizeHist(gray)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return thresh
        
    except Exception as e:
        print(f"Error enhancing image: {e}")
        return image

def get_qr_code_info(qr_data):
    """
    Get detailed information about QR code
    Args:
        qr_data (str): QR code data
    Returns:
        dict: QR code information
    """
    decoded = decode_qr_data(qr_data)
    
    if not decoded:
        return {'error': 'Invalid QR code format'}
    
    # Calculate age of QR code
    qr_timestamp = datetime.fromtimestamp(decoded['timestamp'])
    age = datetime.utcnow() - qr_timestamp
    
    return {
        'student_id': decoded['student_id'],
        'student_no': decoded['student_no'],
        'created_at': qr_timestamp.isoformat(),
        'age_days': age.days,
        'age_hours': age.total_seconds() / 3600,
        'is_recent': age.days < 30,
        'is_valid': age.days < 365
    }