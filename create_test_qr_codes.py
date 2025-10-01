#!/usr/bin/env python3
"""
Student QR Code Generator
Creates valid QR codes for testing the attendance system
"""

import qrcode
from PIL import Image
import json
import os

def create_student_qr_codes():
    """Create valid student QR codes for testing"""
    
    # Get current students from database
    try:
        import sys
        sys.path.insert(0, '.')
        from app import create_app
        from app.models import Student
        
        app = create_app()
        with app.app_context():
            students = Student.query.limit(5).all()
            
            print("🎓 Creating QR Codes for Current Students")
            print("=" * 50)
            
            created_qrs = []
            
            for student in students:
                # Create QR code with student's actual QR data
                qr_data = student.qr_code_data if student.qr_code_data else f"STU{student.id:03d}"
                
                filename = f"student_qr_{student.id}_{student.get_full_name().replace(' ', '_')}.png"
                
                try:
                    # Create high-quality QR code
                    qr = qrcode.QRCode(
                        version=2,  # Larger version for better scanning
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=12,  # Larger boxes
                        border=6,    # Larger border
                    )
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    
                    # Create high-contrast image
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Make it larger for better scanning
                    img = img.resize((400, 400), Image.Resampling.NEAREST)
                    
                    img.save(filename)
                    
                    print(f"✅ Created: {filename}")
                    print(f"   Student: {student.get_full_name()} ({student.student_no})")
                    print(f"   QR Data: {qr_data}")
                    print(f"   File Size: {os.path.getsize(filename)} bytes")
                    print()
                    
                    created_qrs.append({
                        'file': filename,
                        'student': student.get_full_name(),
                        'student_no': student.student_no,
                        'qr_data': qr_data
                    })
                    
                except Exception as e:
                    print(f"❌ Failed to create QR for {student.get_full_name()}: {e}")
            
            return created_qrs
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
        # Fallback: create generic test QR codes
        print("\n🔧 Creating Generic Test QR Codes")
        print("=" * 50)
        
        test_students = [
            {'name': 'John Smith', 'student_no': 'STU001', 'qr_data': 'SCANME_d11a552c0e9f57f7be5c04a25146b27d'},
            {'name': 'Johnrick Nuñeza', 'student_no': 'STU588', 'qr_data': 'SCANME_e22b663d1f0g68g8cf6d15b36257c38e'},
            {'name': 'Test Student', 'student_no': 'STU999', 'qr_data': 'STU999'}
        ]
        
        created_qrs = []
        
        for student in test_students:
            filename = f"test_{student['student_no']}_{student['name'].replace(' ', '_')}.png"
            
            try:
                qr = qrcode.QRCode(
                    version=2,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=12,
                    border=6,
                )
                qr.add_data(student['qr_data'])
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                img = img.resize((400, 400), Image.Resampling.NEAREST)
                img.save(filename)
                
                print(f"✅ Created: {filename}")
                print(f"   Student: {student['name']} ({student['student_no']})")
                print(f"   QR Data: {student['qr_data']}")
                print()
                
                created_qrs.append({
                    'file': filename,
                    'student': student['name'],
                    'student_no': student['student_no'],
                    'qr_data': student['qr_data']
                })
                
            except Exception as e:
                print(f"❌ Failed to create test QR: {e}")
        
        return created_qrs

def create_troubleshooting_guide(created_qrs):
    """Create a troubleshooting guide"""
    
    guide = """
# 🔍 QR CODE TESTING TROUBLESHOOTING GUIDE

## 📋 QR Codes Created for Testing

"""
    
    for qr in created_qrs:
        guide += f"""
### {qr['student']} ({qr['student_no']})
- **File**: `{qr['file']}`
- **QR Data**: `{qr['qr_data']}`
- **Usage**: Upload this image to test QR scanning

"""
    
    guide += """
## 🧪 Testing Steps

1. **Upload Test**: Use any of the generated QR code images above
2. **Camera Test**: Display QR code on screen and use camera scanner
3. **Manual Test**: Copy QR data and use manual input

## 🔧 Common Issues & Solutions

### "No QR code found in the image"
**Possible Causes:**
- Image is blurry or low quality
- QR code is too small or too large
- Image has poor contrast
- QR code is damaged or incomplete

**Solutions:**
✅ Use the high-quality QR codes generated by this tool
✅ Ensure good lighting when taking photos
✅ Make sure QR code fills most of the image
✅ Use PNG format images for best quality

### QR Code Detection Tips
- **Image Size**: 200x200 to 1000x1000 pixels ideal
- **File Format**: PNG or JPEG recommended
- **Contrast**: Black QR code on white background
- **Quality**: Clear, sharp edges
- **Angle**: QR code should be straight, not rotated

### Testing Your QR Image
1. Open the generated QR code file
2. Verify it's clear and readable
3. Upload it to the attendance system
4. Check the console for any error messages

## 🎯 Expected Behavior

When you upload a valid QR code image:
1. ✅ File validation should pass
2. ✅ QR detection should find the code
3. ✅ Student should be identified
4. ✅ Attendance should be recorded

## 📞 If Issues Persist

1. **Check Browser Console**: Look for JavaScript errors
2. **Check Flask Logs**: See server-side error messages
3. **Test Different Images**: Try multiple QR codes
4. **Verify Student Exists**: Ensure student is in database

---
*Generated by QR Code Testing Tool*
"""
    
    with open('QR_TESTING_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print("📖 Created: QR_TESTING_GUIDE.md")

def main():
    """Main function"""
    print("🎯 STUDENT QR CODE GENERATOR")
    print("=" * 50)
    print("Creating high-quality QR codes for testing attendance system")
    print()
    
    created_qrs = create_student_qr_codes()
    
    if created_qrs:
        print(f"🎉 Successfully created {len(created_qrs)} QR codes!")
        print("\n📖 Creating troubleshooting guide...")
        create_troubleshooting_guide(created_qrs)
        
        print("\n🎯 NEXT STEPS:")
        print("1. Use any of the generated QR code images for testing")
        print("2. Upload them through the attendance system")
        print("3. Check QR_TESTING_GUIDE.md for troubleshooting")
        print()
        print("📁 Files created:")
        for qr in created_qrs:
            print(f"   • {qr['file']} - {qr['student']}")
    else:
        print("❌ No QR codes were created")

if __name__ == "__main__":
    main()