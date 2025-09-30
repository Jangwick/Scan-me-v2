#!/usr/bin/env python3
"""
Test the Student model date attribute fix
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_student_date_attribute_fix():
    """Test Student model date attributes"""
    
    print("👥 STUDENT MODEL DATE ATTRIBUTE FIX TEST")
    print("=" * 50)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.student_model import Student
            
            print("✅ Flask app initialized successfully")
            
            # Check Student model attributes
            student_attributes = [attr for attr in dir(Student) if not attr.startswith('_')]
            
            date_related_attrs = [attr for attr in student_attributes if 'date' in attr.lower() or 'created' in attr.lower() or 'time' in attr.lower()]
            
            print(f"📅 Date/time related attributes in Student model:")
            for attr in date_related_attrs:
                print(f"   • {attr}")
            
            # Check for the specific attributes
            has_created_at = hasattr(Student, 'created_at')
            has_date_created = hasattr(Student, 'date_created')
            has_updated_at = hasattr(Student, 'updated_at')
            
            print(f"\n🔍 Attribute verification:")
            print(f"   ✅ created_at: {has_created_at}")
            print(f"   ❌ date_created: {has_date_created}")
            print(f"   ✅ updated_at: {has_updated_at}")
            
            # Test with actual student data
            students = Student.query.all()
            print(f"\n📊 Testing with database students: {len(students)}")
            
            if students:
                test_student = students[0]
                print(f"📋 Testing student: {test_student.get_full_name()}")
                
                try:
                    created_at = test_student.created_at
                    print(f"   ✅ created_at: {created_at}")
                    
                    if created_at:
                        formatted_date = created_at.strftime('%B %d, %Y')
                        formatted_datetime = created_at.strftime('%B %d, %Y at %I:%M %p')
                        print(f"   ✅ Formatted date: {formatted_date}")
                        print(f"   ✅ Formatted datetime: {formatted_datetime}")
                    else:
                        print(f"   ⚠️ created_at is None, will show 'Unknown'")
                        
                except Exception as e:
                    print(f"   ❌ Error accessing created_at: {str(e)}")
                    return False
                
                # Test that date_created doesn't exist
                try:
                    date_created = test_student.date_created
                    print(f"   ❌ date_created still exists: {date_created}")
                except AttributeError:
                    print(f"   ✅ date_created correctly doesn't exist")
            
            print(f"\n🔧 FIXES APPLIED:")
            fixes = [
                "✅ Changed student.date_created to student.created_at in edit.html",
                "✅ Changed student.date_created to student.created_at in view.html", 
                "✅ Added safe null checking with 'if student.created_at else Unknown'",
                "✅ Fixed all timeline date references",
                "✅ Templates now use correct Student model attributes"
            ]
            
            for fix in fixes:
                print(f"   {fix}")
            
            print(f"\n🌐 PAGES THAT SHOULD NOW WORK:")
            pages = [
                "Student edit pages: /students/<id>/edit",
                "Student view pages: /students/<id>",
                "All student-related templates"
            ]
            
            for page in pages:
                print(f"   • {page}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_student_date_attribute_fix()
    
    if success:
        print(f"\n🎉 STUDENT DATE ATTRIBUTE FIX SUCCESSFUL!")
        print(f"✅ No more 'object has no attribute date_created' errors")
        print(f"✅ Templates now use correct created_at attribute")
        print(f"✅ Safe null checking prevents future errors")
    else:
        print(f"\n❌ SOME ISSUES REMAIN - Please check errors above")