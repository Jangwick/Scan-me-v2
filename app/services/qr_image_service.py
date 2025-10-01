"""
QR Code Image Processing Service
Handles edge cases for QR code detection from uploaded images
"""
import io
import logging
from typing import Optional, List, Dict, Any
from PIL import Image

# Optional imports with fallbacks
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    pyzbar = None

logger = logging.getLogger(__name__)

class QRImageProcessingService:
    """
    Service for processing QR codes from uploaded images
    Handles various edge cases from QR_ATTENDANCE_EDGE_CASES.md
    """
    
    # Maximum file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # Supported image formats
    SUPPORTED_FORMATS = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 
        'image/gif', 'image/tiff', 'image/webp'
    }
    
    # Image processing parameters
    MAX_IMAGE_WIDTH = 2048
    MAX_IMAGE_HEIGHT = 2048
    
    @classmethod
    def validate_image_file(cls, file) -> Dict[str, Any]:
        """
        Validate uploaded image file against edge cases
        
        Edge Cases Handled:
        - Wrong File Format: Non-image files
        - Oversized Files: Extremely large files
        - Empty/No File: Missing file data
        
        Returns:
            dict: {'valid': bool, 'error': str or None}
        """
        try:
            # Check if file exists
            if not file:
                return {'valid': False, 'error': 'No file provided'}
            
            # Check filename
            if not file.filename or file.filename == '':
                return {'valid': False, 'error': 'No file selected'}
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)     # Reset to beginning
            
            if file_size == 0:
                return {'valid': False, 'error': 'File is empty'}
            
            if file_size > cls.MAX_FILE_SIZE:
                return {'valid': False, 'error': f'File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size (5MB)'}
            
            # Check content type
            if hasattr(file, 'content_type') and file.content_type not in cls.SUPPORTED_FORMATS:
                return {'valid': False, 'error': f'Unsupported file format: {file.content_type}. Please use JPEG, PNG, BMP, GIF, TIFF, or WebP.'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            logger.error(f"Error validating image file: {str(e)}")
            return {'valid': False, 'error': 'Failed to validate file'}
    
    @classmethod
    def extract_qr_codes(cls, file) -> Dict[str, Any]:
        """
        Extract QR code data from uploaded image file
        
        Edge Cases Handled:
        - Corrupted Images: Unreadable or damaged files
        - Multiple QR Codes: Images with multiple QR codes
        - No QR Code Found: Images without QR codes
        - Poor Image Quality: Blurry, low-resolution images
        - Binary Data: Non-text QR code content
        - Missing Dependencies: Graceful fallback when libraries unavailable
        
        Returns:
            dict: {
                'success': bool,
                'qr_codes': List[str],
                'error': str or None,
                'details': dict
            }
        """
        try:
            # Check if QR detection libraries are available
            if not PYZBAR_AVAILABLE:
                return {
                    'success': False,
                    'qr_codes': [],
                    'error': 'QR code detection libraries not available. Please install pyzbar.',
                    'details': {'missing_libraries': ['pyzbar']}
                }
            
            # Read the uploaded file
            image_data = file.read()
            
            if not image_data:
                return {
                    'success': False,
                    'qr_codes': [],
                    'error': 'File contains no data',
                    'details': {'file_size': 0}
                }
            
            # Try to open with PIL
            try:
                image = Image.open(io.BytesIO(image_data))
            except Exception as e:
                logger.error(f"Failed to open image with PIL: {str(e)}")
                return {
                    'success': False,
                    'qr_codes': [],
                    'error': 'Corrupted or invalid image file',
                    'details': {'pil_error': str(e)}
                }
            
            # Check image dimensions
            width, height = image.size
            if width > cls.MAX_IMAGE_WIDTH or height > cls.MAX_IMAGE_HEIGHT:
                # Resize large images to improve processing speed
                image.thumbnail((cls.MAX_IMAGE_WIDTH, cls.MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                logger.info(f"Resized large image from {width}x{height} to {image.size}")
            
            # Convert to RGB if necessary (handle different color modes)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Detect QR codes using available methods
            qr_codes = cls._detect_qr_codes_with_available_libraries(image)
            
            if not qr_codes:
                return {
                    'success': False,
                    'qr_codes': [],
                    'error': 'No QR code found in the image. Please ensure the image contains a clear, valid student QR code.',
                    'details': {
                        'image_size': f"{width}x{height}",
                        'file_size': len(image_data),
                        'cv2_available': CV2_AVAILABLE,
                        'pyzbar_available': PYZBAR_AVAILABLE
                    }
                }
            
            # Validate QR code data
            valid_qr_codes = []
            invalid_qr_codes = []
            
            for qr_data in qr_codes:
                validation_result = cls._validate_qr_data(qr_data)
                if validation_result['valid']:
                    valid_qr_codes.append(qr_data)
                else:
                    invalid_qr_codes.append({
                        'data': qr_data,
                        'error': validation_result['error']
                    })
            
            if not valid_qr_codes:
                return {
                    'success': False,
                    'qr_codes': [],
                    'error': 'QR code found but contains invalid data format',
                    'details': {
                        'invalid_codes': invalid_qr_codes,
                        'total_detected': len(qr_codes)
                    }
                }
            
            # Handle multiple QR codes
            if len(valid_qr_codes) > 1:
                logger.warning(f"Multiple QR codes detected: {valid_qr_codes}")
                # Use the first valid QR code
                return {
                    'success': True,
                    'qr_codes': [valid_qr_codes[0]],
                    'error': None,
                    'details': {
                        'total_detected': len(qr_codes),
                        'valid_codes': len(valid_qr_codes),
                        'note': 'Multiple QR codes found, using first valid one'
                    }
                }
            
            return {
                'success': True,
                'qr_codes': valid_qr_codes,
                'error': None,
                'details': {
                    'image_size': f"{width}x{height}",
                    'file_size': len(image_data),
                    'detection_method': 'pyzbar' + (' + opencv' if CV2_AVAILABLE else '')
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting QR codes from image: {str(e)}")
            return {
                'success': False,
                'qr_codes': [],
                'error': 'Failed to process image',
                'details': {'exception': str(e)}
            }
    
    @classmethod
    def _detect_qr_codes_with_available_libraries(cls, pil_image) -> List[str]:
        """
        Detect QR codes using available libraries with fallback methods
        """
        qr_codes = []
        
        if not PYZBAR_AVAILABLE:
            logger.warning("pyzbar not available, cannot detect QR codes from images")
            return qr_codes
        
        # Method 1: Direct PIL to pyzbar detection
        try:
            detected = pyzbar.decode(pil_image)
            for qr in detected:
                try:
                    data = qr.data.decode('utf-8')
                    qr_codes.append(data)
                except UnicodeDecodeError:
                    logger.warning(f"QR code contains binary data: {qr.data}")
                    continue
        except Exception as e:
            logger.debug(f"PIL direct detection failed: {str(e)}")
        
        # If OpenCV is available, try enhanced methods
        if CV2_AVAILABLE and not qr_codes:
            try:
                # Convert PIL to OpenCV format
                opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                qr_codes = cls._detect_qr_codes_multiple_methods(opencv_image)
            except Exception as e:
                logger.debug(f"OpenCV detection failed: {str(e)}")
        
        # If still no QR codes and we have basic image processing, try simple enhancements
        if not qr_codes:
            try:
                # Convert to grayscale using PIL
                gray_image = pil_image.convert('L')
                detected = pyzbar.decode(gray_image)
                for qr in detected:
                    try:
                        data = qr.data.decode('utf-8')
                        if data not in qr_codes:
                            qr_codes.append(data)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"Grayscale detection failed: {str(e)}")
        
        return qr_codes
    
    @classmethod
    def _detect_qr_codes_multiple_methods(cls, opencv_image) -> List[str]:
        """
        Try multiple detection methods for better success rate
        Handles edge case: Poor Image Quality
        Only works when OpenCV is available
        """
        qr_codes = []
        
        if not CV2_AVAILABLE or not PYZBAR_AVAILABLE:
            return qr_codes
        
        # Method 1: Direct detection
        try:
            detected = pyzbar.decode(opencv_image)
            for qr in detected:
                try:
                    data = qr.data.decode('utf-8')
                    qr_codes.append(data)
                except UnicodeDecodeError:
                    # Handle binary data edge case
                    logger.warning(f"QR code contains binary data: {qr.data}")
                    continue
        except Exception as e:
            logger.debug(f"Direct detection failed: {str(e)}")
        
        # If no QR codes found, try image enhancement methods
        if not qr_codes:
            # Method 2: Convert to grayscale
            try:
                gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
                detected = pyzbar.decode(gray)
                for qr in detected:
                    try:
                        data = qr.data.decode('utf-8')
                        if data not in qr_codes:
                            qr_codes.append(data)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"Grayscale detection failed: {str(e)}")
        
        # Method 3: Apply Gaussian blur to reduce noise
        if not qr_codes:
            try:
                blurred = cv2.GaussianBlur(opencv_image, (3, 3), 0)
                detected = pyzbar.decode(blurred)
                for qr in detected:
                    try:
                        data = qr.data.decode('utf-8')
                        if data not in qr_codes:
                            qr_codes.append(data)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"Blur detection failed: {str(e)}")
        
        # Method 4: Enhance contrast
        if not qr_codes:
            try:
                # Convert to LAB color space and enhance L channel
                lab = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                enhanced = cv2.merge([l, a, b])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                
                detected = pyzbar.decode(enhanced)
                for qr in detected:
                    try:
                        data = qr.data.decode('utf-8')
                        if data not in qr_codes:
                            qr_codes.append(data)
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"Contrast enhancement detection failed: {str(e)}")
        
        return qr_codes
    
    @classmethod
    def _validate_qr_data(cls, qr_data: str) -> Dict[str, Any]:
        """
        Validate QR code data format
        
        Edge Cases Handled:
        - Empty QR Code: Empty string or whitespace
        - Unicode Characters: Special characters, emojis
        - Extremely Long Data: QR codes exceeding limits
        - HTML/Script Injection: Malicious content
        - Invalid Data Types: Non-string content
        """
        try:
            # Check for empty/whitespace data
            if not qr_data or not qr_data.strip():
                return {'valid': False, 'error': 'QR code contains empty or whitespace-only data'}
            
            # Check data length (reasonable limit)
            if len(qr_data) > 1000:  # Reasonable limit for QR codes
                return {'valid': False, 'error': f'QR code data too long ({len(qr_data)} characters)'}
            
            # Check for potential script injection
            dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:', '<iframe']
            qr_lower = qr_data.lower()
            for pattern in dangerous_patterns:
                if pattern in qr_lower:
                    return {'valid': False, 'error': 'QR code contains potentially malicious content'}
            
            # Basic format validation - should be student QR format
            # Expected formats: SCANME_hash, STU123, or JSON
            if qr_data.startswith('SCANME_') or qr_data.startswith('STU') or qr_data.startswith('{'):
                return {'valid': True, 'error': None}
            
            # Try to parse as JSON for legacy formats
            try:
                import json
                parsed = json.loads(qr_data)
                if isinstance(parsed, dict) and ('student_id' in parsed or 'student_no' in parsed):
                    return {'valid': True, 'error': None}
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Allow other formats but log them
            logger.info(f"QR code with non-standard format detected: {qr_data[:50]}...")
            return {'valid': True, 'error': None}
            
        except Exception as e:
            logger.error(f"Error validating QR data: {str(e)}")
            return {'valid': False, 'error': 'Failed to validate QR code data'}