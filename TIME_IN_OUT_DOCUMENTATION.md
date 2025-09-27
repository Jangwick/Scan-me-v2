# Time-In/Time-Out Attendance System

## Overview

The ScanMe Attendance System now supports comprehensive time-in and time-out functionality, allowing students to scan their QR codes when entering a classroom (time-in) and when leaving (time-out). This provides complete tracking of student presence and duration in classrooms.

## Features

### 🎯 Core Functionality
- **Time-In Scanning**: Students scan QR code when entering classroom
- **Time-Out Scanning**: Students scan QR code when leaving classroom  
- **Smart Detection**: System automatically determines if student should time-in or time-out
- **Duration Tracking**: Calculates how long students spent in classroom
- **Real-time Status**: Shows who is currently in each room

### 📊 Enhanced Tracking
- **Active Status**: Track which students are currently in classrooms
- **Visit Duration**: Calculate exact time spent in each class
- **Multiple Visits**: Support for students entering/leaving multiple times
- **Historical Records**: Complete history of all time-in and time-out events

### 🎛️ Flexible Scanning Modes
- **Auto Mode**: Smart detection based on current student status
- **Time-In Only**: Force time-in regardless of current status
- **Time-Out Only**: Force time-out regardless of current status

## Database Schema Changes

### New Columns Added to `attendance_records`
```sql
- time_in DATETIME NOT NULL (when student entered)
- time_out DATETIME NULL (when student left, null if still in room)
- is_active BOOLEAN DEFAULT TRUE (true if student currently in room)
- time_in_scanned_by INTEGER (user who scanned time-in)
- time_out_scanned_by INTEGER (user who scanned time-out)
```

### Backward Compatibility
- Original `scan_time` column maintained for legacy support
- Original `scanned_by` column maintained for legacy support
- Existing data automatically migrated

## API Endpoints

### Scanner API Updates

#### POST `/scanner/api/scan-qr`
Enhanced to support time-in/time-out functionality.

**Request Body:**
```json
{
  "qr_data": "student_qr_code_content",
  "session_id": 123,
  "scan_type": "auto|time_in|time_out"
}
```

**Response Examples:**

**Time-In Success:**
```json
{
  "success": true,
  "message": "Successfully timed in John Doe",
  "student_name": "John Doe",
  "action": "time_in",
  "is_late": false,
  "time_in": "2025-09-27T10:30:00",
  "timestamp": "2025-09-27T10:30:00"
}
```

**Time-Out Success:**
```json
{
  "success": true,
  "message": "Successfully timed out John Doe. Duration: 120 minutes",
  "student_name": "John Doe", 
  "action": "time_out",
  "time_in": "2025-09-27T08:30:00",
  "time_out": "2025-09-27T10:30:00",
  "duration_minutes": 120,
  "timestamp": "2025-09-27T10:30:00"
}
```

### Statistics API Updates

#### GET `/scanner/api/session-stats/{session_id}`
**Response:**
```json
{
  "total_time_ins": 25,
  "completed_visits": 15,
  "currently_in_room": 10,
  "unique_students": 25,
  "late_arrivals": 3,
  "avg_duration_minutes": 95.5
}
```

#### GET `/scanner/api/today-stats`
**Response:**
```json
{
  "total_time_ins": 150,
  "completed_visits": 120,
  "currently_in_rooms": 30,
  "unique_students": 145
}
```

### New API Endpoints

#### GET `/scanner/api/current-occupancy/{session_id}`
Get list of students currently in a room.

**Response:**
```json
{
  "success": true,
  "session_name": "Math 101 - Morning Class",
  "room_name": "Room A-101", 
  "current_occupancy": 2,
  "students": [
    {
      "student_id": 1,
      "student_name": "John Doe",
      "student_no": "STU001",
      "time_in": "2025-09-27T08:30:00",
      "duration_minutes": 45,
      "is_late": false
    }
  ]
}
```

## User Interface Updates

### Scanner Interface Enhancements

1. **Scan Mode Selector**
   - Dropdown to choose scanning mode (Auto/Time-In Only/Time-Out Only)
   - Smart default selection based on context

2. **Enhanced Status Display**
   - Shows time-in and time-out actions with different icons
   - Duration information for completed visits
   - Real-time status indicators

3. **Improved Statistics Panel**
   - "Time Ins" instead of generic "Scans"
   - "Currently In" to show active students
   - Session-specific occupancy data

### Recent Activity Updates
- Icons distinguish between time-in (↗️) and time-out (↖️) actions
- Duration shown for completed visits
- Color coding for different action types

## Usage Instructions

### For Students

#### Time-In Process:
1. Enter classroom
2. Open scanner or show QR code to admin
3. Scan QR code (system automatically detects time-in needed)
4. Confirmation: "✅ TIME IN: John Doe"

#### Time-Out Process:
1. Prepare to leave classroom  
2. Scan QR code again (system detects time-out needed)
3. Confirmation: "⏰ TIME OUT: John Doe (Duration: 90 min)"

### For Administrators/Professors

#### Scanner Operation:
1. **Select Session**: Choose active classroom session
2. **Choose Scan Mode**: 
   - Auto: Let system decide time-in vs time-out
   - Time-In Only: Force all scans as time-in
   - Time-Out Only: Force all scans as time-out
3. **Scan QR Codes**: Process student QR codes
4. **Monitor Status**: View real-time room occupancy

#### Manual Override:
- Use "Time-In Only" mode to force time-in for late students
- Use "Time-Out Only" mode during dismissal
- Auto mode handles 95% of normal operations

## Business Logic

### Smart Detection Algorithm:
1. **Check Active Records**: Does student have active record in this room?
2. **If Active Record Exists**: Process as time-out
3. **If No Active Record**: Process as time-in
4. **Duplicate Prevention**: Block multiple time-ins within 5 minutes

### Late Arrival Detection:
- Students arriving >10 minutes after session start marked as late
- Late status affects only time-in, not time-out

### Duration Calculation:
- **Active Students**: Duration = Current Time - Time In
- **Completed Visits**: Duration = Time Out - Time In
- **Precision**: Calculated to the minute

## Data Model

### AttendanceRecord Enhanced Structure:
```python
class AttendanceRecord(db.Model):
    # Primary tracking
    time_in = DateTime(required)      # When student entered
    time_out = DateTime(optional)     # When student left
    is_active = Boolean(default=True) # Currently in room?
    
    # Scanner information  
    time_in_scanned_by = ForeignKey(User)   # Who scanned time-in
    time_out_scanned_by = ForeignKey(User)  # Who scanned time-out
    
    # Methods
    def get_duration(self) -> int         # Duration in minutes
    def get_status(self) -> str           # in_room, timed_out, unknown  
    def time_out_student(self, user_id)   # Process time-out
```

### Key Methods:
- `AttendanceRecord.get_student_active_record(student_id, room_id)` - Get active record for student in room
- `AttendanceRecord.get_active_in_room(room_id)` - Get all active students in room
- `attendance.time_out_student(user_id)` - Process time-out for student

## Migration Guide

### For Existing Installations:

1. **Run Database Migration:**
   ```bash
   python migrate_attendance_db.py
   ```

2. **Test Functionality:**
   ```bash
   python test_time_in_out.py
   ```

3. **Verify Scanner Interface:**
   - Visit `/scanner/` route
   - Check for new scan mode selector
   - Test time-in and time-out flows

### Migration Details:
- Existing records marked as inactive (`is_active = False`)
- `scan_time` data copied to `time_in` field
- `scanned_by` data copied to `time_in_scanned_by` field
- No data loss - all existing functionality preserved

## Benefits

### For Students:
- **Accurate Tracking**: Complete record of classroom presence
- **Flexible Movement**: Can leave and return to classroom
- **Duration Records**: Personal attendance duration tracking

### For Instructors:
- **Real-time Occupancy**: Know exactly who is in classroom
- **Duration Analytics**: Understand student engagement patterns
- **Flexible Policies**: Support different attendance requirements

### For Administrators:
- **Complete Records**: Full audit trail of student movements
- **Room Utilization**: Detailed room usage statistics
- **Compliance**: Meet institutional attendance tracking requirements

## Security & Validation

### Duplicate Prevention:
- Block multiple time-ins within 5-minute window
- Require time-out before new time-in
- Validate student and session relationships

### Data Integrity:
- Foreign key constraints on all relationships
- Automatic timestamp generation
- Rollback protection on errors

### Access Control:
- Authentication required for all scanner operations
- User tracking for audit purposes
- Session-based access control

## Performance Considerations

### Database Optimization:
- Indexed on frequently queried columns (`student_id`, `room_id`, `time_in`, `is_active`)
- Efficient queries for active record lookups
- Optimized statistics calculations

### Real-time Updates:
- 30-second auto-refresh for statistics
- Immediate UI updates after scan operations
- Efficient recent activity queries

## Future Enhancements

### Planned Features:
- Push notifications for time-out reminders
- Automatic time-out after maximum duration
- Batch time-out operations
- Advanced reporting and analytics
- Mobile app integration
- RFID card support

### API Extensibility:
- RESTful design allows easy integration
- JSON responses support mobile apps
- Webhook support for external systems

## Troubleshooting

### Common Issues:

**Student appears "stuck" in room:**
- Check for active record: `AttendanceRecord.get_student_active_record(student_id, room_id)`
- Manually time out: `record.time_out_student(admin_user_id)`

**Time-in blocked with "already timed in":**
- Student has active record in room
- Use "Time-Out Only" mode first, then time-in again

**Statistics not updating:**
- Check session selection
- Verify database connectivity
- Check browser console for errors

**Migration Issues:**
- Backup database before migration
- Run migration script: `python migrate_attendance_db.py`
- Test with: `python test_time_in_out.py`

## Support

For technical support or feature requests, refer to the project documentation or contact the system administrator.

---

*Last updated: September 27, 2025*
*Version: 2.0 - Time-In/Time-Out Release*