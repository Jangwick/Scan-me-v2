from app.utils.qr_utils import validate_qr_data

test_qr = '{"type": "student_attendance", "student_id": "abc", "student_no": "123", "name": "Test"}'
result = validate_qr_data(test_qr)
print(f"Valid: {result['valid']}")
print(f"Error: {result.get('error')}")
print(f"Error Code: {result.get('error_code')}")