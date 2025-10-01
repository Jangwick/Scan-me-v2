"""
Attendance State Management Service
Handles time-in/time-out logic with comprehensive edge case handling

This service implements all the edge cases from QR_ATTENDANCE_EDGE_CASES.md:
- State Management Edge Cases
- Time Calculation Edge Cases  
- Smart Detection Logic
"""

from app import db
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.attendance_event_model import AttendanceEvent
from app.models.student_model import Student
from app.models.room_model import Room
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, or_, func
import logging
import json

logger = logging.getLogger(__name__)

class AttendanceStateService:
    """Service for managing attendance state with edge case handling"""
    
    # Configuration constants
    RAPID_SCAN_THRESHOLD = 5  # seconds
    DUPLICATE_SCAN_WINDOW = 300  # 5 minutes in seconds
    EXTREME_DURATION_HOURS = 24  # hours
    MAX_CONCURRENT_ACTIVE_RECORDS = 1  # per student per room
    GRACE_PERIOD_MINUTES = 10  # late arrival grace period
    
    @staticmethod
    def process_attendance_scan(student_id, room_id, session_id, scanned_by, scan_type='auto', 
                              user_agent=None, ip_address=None):
        """
        Main entry point for processing attendance scans with comprehensive edge case handling
        
        Args:
            student_id: ID of the student
            room_id: ID of the room
            session_id: ID of the session (optional)
            scanned_by: ID of the user performing the scan
            scan_type: 'auto', 'time_in', 'time_out'
            user_agent: Browser user agent
            ip_address: Client IP address
            
        Returns:
            dict: Result with success status, message, and action details
        """
        try:
            # Validate inputs
            validation_result = AttendanceStateService._validate_scan_inputs(
                student_id, room_id, session_id, scanned_by
            )
            if not validation_result['valid']:
                return validation_result
            
            student = validation_result['student']
            room = validation_result['room']
            session = validation_result.get('session')
            
            # Check for rapid sequential scans
            rapid_scan_check = AttendanceStateService._check_rapid_sequential_scans(
                student_id, room_id
            )
            if not rapid_scan_check['allowed']:
                return rapid_scan_check
            
            # Get current state
            state_analysis = AttendanceStateService._analyze_current_state(
                student_id, room_id, session_id
            )
            
            # Determine action based on scan type and current state
            action_decision = AttendanceStateService._determine_action(
                scan_type, state_analysis, student, room, session
            )
            
            if action_decision['action'] == 'time_in':
                return AttendanceStateService._process_time_in(
                    student, room, session, scanned_by, state_analysis,
                    user_agent, ip_address
                )
            elif action_decision['action'] == 'time_out':
                return AttendanceStateService._process_time_out(
                    student, room, session, scanned_by, state_analysis,
                    user_agent, ip_address
                )
            else:
                return action_decision
                
        except Exception as e:
            logger.error(f"Error in process_attendance_scan: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'System error occurred during scan processing',
                'error_code': 'SYSTEM_ERROR',
                'action': 'error'
            }
    
    @staticmethod
    def _validate_scan_inputs(student_id, room_id, session_id, scanned_by):
        """Validate all scan inputs and return entities"""
        try:
            # Get student
            student = Student.query.get(student_id)
            if not student:
                return {
                    'valid': False,
                    'success': False,
                    'message': 'Student not found',
                    'error_code': 'STUDENT_NOT_FOUND'
                }
            
            if not student.is_active:
                return {
                    'valid': False,
                    'success': False,
                    'message': 'Student account is inactive',
                    'error_code': 'STUDENT_INACTIVE'
                }
            
            # Get room
            room = Room.query.get(room_id)
            if not room:
                return {
                    'valid': False,
                    'success': False,
                    'message': 'Room not found',
                    'error_code': 'ROOM_NOT_FOUND'
                }
            
            if not room.is_active:
                return {
                    'valid': False,
                    'success': False,
                    'message': 'Room is inactive',
                    'error_code': 'ROOM_INACTIVE'
                }
            
            # Get session (optional)
            session = None
            if session_id:
                session = AttendanceSession.query.get(session_id)
                if not session:
                    return {
                        'valid': False,
                        'success': False,
                        'message': 'Session not found',
                        'error_code': 'SESSION_NOT_FOUND'
                    }
                
                if not session.is_active:
                    return {
                        'valid': False,
                        'success': False,
                        'message': 'Session is inactive',
                        'error_code': 'SESSION_INACTIVE'
                    }
            
            return {
                'valid': True,
                'student': student,
                'room': room,
                'session': session
            }
            
        except Exception as e:
            logger.error(f"Error validating scan inputs: {str(e)}")
            return {
                'valid': False,
                'success': False,
                'message': 'Validation error occurred',
                'error_code': 'VALIDATION_ERROR'
            }
    
    @staticmethod
    def _check_rapid_sequential_scans(student_id, room_id):
        """Check for rapid sequential scans (Edge Case: Double Scanning)"""
        try:
            threshold_time = datetime.utcnow() - timedelta(seconds=AttendanceStateService.RAPID_SCAN_THRESHOLD)
            
            recent_scan = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.time_in >= threshold_time
            ).first()
            
            if recent_scan:
                return {
                    'allowed': False,
                    'success': False,
                    'message': f'Please wait {AttendanceStateService.RAPID_SCAN_THRESHOLD} seconds between scans',
                    'error_code': 'RAPID_SCAN_DETECTED',
                    'action': 'rate_limited'
                }
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Error checking rapid scans: {str(e)}")
            return {'allowed': True}  # Allow scan if check fails
    
    @staticmethod
    def _analyze_current_state(student_id, room_id, session_id):
        """Analyze current attendance state for the student"""
        try:
            # Get active records for student in this room
            active_records = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.is_active == True
            ).all()
            
            # Get active records for student in other rooms (Edge Case: Multiple Rooms)
            other_room_active = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id != room_id,
                AttendanceRecord.is_active == True
            ).all()
            
            # Check for orphaned active records (Edge Case: Missing Time-Out)
            orphaned_records = AttendanceStateService._detect_orphaned_records(student_id)
            
            # Get recent scans in duplicate window
            duplicate_window = datetime.utcnow() - timedelta(seconds=AttendanceStateService.DUPLICATE_SCAN_WINDOW)
            recent_scans = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.time_in >= duplicate_window
            ).all()
            
            return {
                'active_records_this_room': active_records,
                'active_records_other_rooms': other_room_active,
                'orphaned_records': orphaned_records,
                'recent_scans': recent_scans,
                'has_multiple_active': len(active_records) > 1,
                'is_in_multiple_rooms': len(other_room_active) > 0,
                'current_status': AttendanceStateService._determine_current_status(active_records)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing current state: {str(e)}")
            return {
                'active_records_this_room': [],
                'active_records_other_rooms': [],
                'orphaned_records': [],
                'recent_scans': [],
                'has_multiple_active': False,
                'is_in_multiple_rooms': False,
                'current_status': 'unknown'
            }
    
    @staticmethod
    def _detect_orphaned_records(student_id):
        """Detect orphaned active records (Edge Case: Missing Time-Out)"""
        try:
            # Find active records older than extreme duration threshold
            threshold_time = datetime.utcnow() - timedelta(hours=AttendanceStateService.EXTREME_DURATION_HOURS)
            
            orphaned = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.is_active == True,
                AttendanceRecord.time_in <= threshold_time
            ).all()
            
            return orphaned
            
        except Exception as e:
            logger.error(f"Error detecting orphaned records: {str(e)}")
            return []
    
    @staticmethod
    def _determine_current_status(active_records):
        """Determine current student status based on active records"""
        if not active_records:
            return 'not_in_room'
        elif len(active_records) == 1:
            return 'in_room'
        else:
            return 'multiple_active'  # Edge case
    
    @staticmethod
    def _determine_action(scan_type, state_analysis, student, room, session):
        """Determine what action to take based on scan type and current state"""
        try:
            current_status = state_analysis['current_status']
            active_records = state_analysis['active_records_this_room']
            
            # Handle multiple active records edge case
            if state_analysis['has_multiple_active']:
                # Clean up multiple active records
                cleanup_result = AttendanceStateService._cleanup_multiple_active_records(
                    active_records, student, room
                )
                if not cleanup_result['success']:
                    return cleanup_result
                # Refresh state after cleanup
                state_analysis = AttendanceStateService._analyze_current_state(
                    student.id, room.id, session.id if session else None
                )
                current_status = state_analysis['current_status']
                active_records = state_analysis['active_records_this_room']
            
            # Handle student in multiple rooms edge case
            if state_analysis['is_in_multiple_rooms']:
                warning_msg = f"Warning: {student.get_full_name()} has active records in other rooms"
                logger.warning(warning_msg)
                # Continue with processing but log the warning
            
            # Determine action based on scan type and state
            if scan_type == 'time_out':
                if current_status == 'not_in_room':
                    return {
                        'success': False,
                        'message': f'{student.get_full_name()} is not currently in this room',
                        'error_code': 'NOT_IN_ROOM',
                        'action': 'error'
                    }
                return {'action': 'time_out'}
                
            elif scan_type == 'time_in':
                if current_status == 'in_room':
                    return {
                        'success': False,
                        'message': f'{student.get_full_name()} is already in this room',
                        'error_code': 'ALREADY_IN_ROOM',
                        'action': 'duplicate'
                    }
                return {'action': 'time_in'}
                
            else:  # scan_type == 'auto'
                # Smart detection logic
                if current_status == 'not_in_room':
                    return {'action': 'time_in'}
                elif current_status == 'in_room':
                    return {'action': 'time_out'}
                else:
                    # Ambiguous state - default to time_in with warning
                    return {
                        'action': 'time_in',
                        'warning': 'Ambiguous state detected, defaulting to time-in'
                    }
            
        except Exception as e:
            logger.error(f"Error determining action: {str(e)}")
            return {
                'success': False,
                'message': 'Error determining scan action',
                'error_code': 'ACTION_DETERMINATION_ERROR',
                'action': 'error'
            }
    
    @staticmethod
    def _cleanup_multiple_active_records(active_records, student, room):
        """Clean up multiple active records edge case"""
        try:
            if len(active_records) <= 1:
                return {'success': True}
            
            # Sort by time_in, keep the most recent, mark others as timed out
            sorted_records = sorted(active_records, key=lambda r: r.time_in, reverse=True)
            most_recent = sorted_records[0]
            
            # Time out older records
            for record in sorted_records[1:]:
                record.time_out = datetime.utcnow()
                record.is_active = False
                record.notes = (record.notes or '') + ' [Auto-timed out due to multiple active records]'
            
            db.session.commit()
            
            logger.warning(f"Cleaned up {len(sorted_records)-1} duplicate active records for student {student.id} in room {room.id}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error cleaning up multiple active records: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'Error cleaning up duplicate records',
                'error_code': 'CLEANUP_ERROR',
                'action': 'error'
            }
    
    @staticmethod
    def _process_time_in(student, room, session, scanned_by, state_analysis, user_agent, ip_address):
        """Process time-in with edge case handling"""
        try:
            now = datetime.utcnow()
            
            # Check for recent duplicate scans
            recent_scans = state_analysis['recent_scans']
            if recent_scans:
                most_recent = max(recent_scans, key=lambda r: r.time_in)
                if (now - most_recent.time_in).total_seconds() < AttendanceStateService.DUPLICATE_SCAN_WINDOW:
                    return {
                        'success': False,
                        'message': f'{student.get_full_name()} has a recent scan in this room',
                        'error_code': 'RECENT_DUPLICATE',
                        'action': 'duplicate',
                        'recent_scan_time': most_recent.time_in.isoformat()
                    }
            
            # Determine if late
            is_late = AttendanceStateService._calculate_late_arrival(session, now)
            
            # Handle time zone consistency
            normalized_time = AttendanceStateService._normalize_time_zone(now)
            
            # Create attendance record
            attendance = AttendanceRecord(
                student_id=student.id,
                room_id=room.id,
                session_id=session.id if session else None,
                scanned_by=scanned_by,
                is_late=is_late
            )
            
            # Set additional metadata
            attendance.ip_address = ip_address
            attendance.user_agent = user_agent
            attendance.time_in = normalized_time
            attendance.scan_time = normalized_time
            
            # Check for duplicates after creation
            attendance.check_and_set_duplicate_status()
            
            db.session.add(attendance)
            db.session.flush()  # Get the attendance ID before creating event
            
            # Create time-in event for audit trail
            time_in_event = AttendanceEvent(
                student_id=student.id,
                room_id=room.id,
                session_id=session.id if session else None,
                scanned_by=scanned_by,
                event_type='time_in',
                ip_address=ip_address,
                user_agent=user_agent,
                attendance_record_id=attendance.id
            )
            # Set the event time to match the normalized time
            time_in_event.event_time = normalized_time
            
            db.session.add(time_in_event)
            db.session.commit()
            
            # Log the time-in
            logger.info(f"Time-in: Student {student.id} in room {room.id} at {normalized_time}")
            
            return {
                'success': True,
                'message': f'Successfully timed in {student.get_full_name()}' + (' (Late)' if is_late else ''),
                'student_name': student.get_full_name(),
                'action': 'time_in',
                'is_late': is_late,
                'time_in': attendance.time_in.isoformat(),
                'timestamp': attendance.time_in.isoformat(),
                'record_id': attendance.id
            }
            
        except Exception as e:
            logger.error(f"Error processing time-in: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'Error processing time-in',
                'error_code': 'TIME_IN_ERROR',
                'action': 'error'
            }
    
    @staticmethod
    def _process_time_out(student, room, session, scanned_by, state_analysis, user_agent, ip_address):
        """Process time-out with edge case handling"""
        try:
            active_records = state_analysis['active_records_this_room']
            
            if not active_records:
                return {
                    'success': False,
                    'message': f'{student.get_full_name()} is not currently in this room',
                    'error_code': 'NOT_IN_ROOM',
                    'action': 'error'
                }
            
            # Use the most recent active record
            active_record = max(active_records, key=lambda r: r.time_in)
            
            # Handle time zone consistency
            now = datetime.utcnow()
            normalized_time = AttendanceStateService._normalize_time_zone(now)
            
            # Validate time-out time (Edge Case: Negative Duration)
            if normalized_time <= active_record.time_in:
                # Clock synchronization issue detected
                logger.warning(f"Clock sync issue: time_out ({normalized_time}) <= time_in ({active_record.time_in})")
                # Use time_in + 1 minute as minimum time_out
                normalized_time = active_record.time_in + timedelta(minutes=1)
            
            # Perform time-out
            active_record.time_out = normalized_time
            active_record.time_out_scanned_by = scanned_by
            active_record.is_active = False
            
            # Calculate duration
            duration = active_record.get_duration()
            
            # Check for extreme duration (Edge Case)
            if duration > (AttendanceStateService.EXTREME_DURATION_HOURS * 60):
                warning_note = f"[Extreme duration detected: {duration} minutes]"
                active_record.notes = (active_record.notes or '') + warning_note
                logger.warning(f"Extreme duration: Student {student.id} in room {room.id} for {duration} minutes")
            
            # Create time-out event for audit trail
            time_out_event = AttendanceEvent(
                student_id=student.id,
                room_id=room.id,
                session_id=session.id if session else None,
                scanned_by=scanned_by,
                event_type='time_out',
                ip_address=ip_address,
                user_agent=user_agent,
                attendance_record_id=active_record.id,
                duration_minutes=duration
            )
            # Set the event time to match the normalized time
            time_out_event.event_time = normalized_time
            
            db.session.add(time_out_event)
            db.session.commit()
            
            # Log the time-out
            logger.info(f"Time-out: Student {student.id} from room {room.id} at {normalized_time}, duration: {duration} minutes")
            
            return {
                'success': True,
                'message': f'Successfully timed out {student.get_full_name()}. Duration: {duration} minutes',
                'student_name': student.get_full_name(),
                'action': 'time_out',
                'time_in': active_record.time_in.isoformat(),
                'time_out': active_record.time_out.isoformat(),
                'duration_minutes': duration,
                'timestamp': active_record.time_out.isoformat(),
                'record_id': active_record.id
            }
            
        except Exception as e:
            logger.error(f"Error processing time-out: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'Error processing time-out',
                'error_code': 'TIME_OUT_ERROR',
                'action': 'error'
            }
    
    @staticmethod
    def _calculate_late_arrival(session, scan_time):
        """Calculate if arrival is late with edge case handling"""
        try:
            if not session or not session.start_time:
                # No session or start time - use default logic
                return scan_time.time() > datetime.now().replace(hour=9, minute=0, second=0, microsecond=0).time()
            
            # Handle time zone issues
            session_start = AttendanceStateService._normalize_time_zone(session.start_time)
            normalized_scan = AttendanceStateService._normalize_time_zone(scan_time)
            
            # Grace period handling
            grace_period_end = session_start + timedelta(minutes=AttendanceStateService.GRACE_PERIOD_MINUTES)
            
            # Edge case: Grace period boundary
            return normalized_scan > grace_period_end
            
        except Exception as e:
            logger.error(f"Error calculating late arrival: {str(e)}")
            return False  # Default to not late if calculation fails
    
    @staticmethod
    def _normalize_time_zone(dt):
        """Normalize datetime to UTC to handle time zone edge cases"""
        try:
            if dt.tzinfo is None:
                # Assume UTC if no timezone info
                return dt.replace(tzinfo=timezone.utc).replace(tzinfo=None)
            else:
                # Convert to UTC and remove timezone info for consistency
                return dt.utctimetuple()
                return datetime.fromtimestamp(dt.timestamp())
        except Exception as e:
            logger.error(f"Error normalizing timezone: {str(e)}")
            return dt  # Return original if normalization fails
    
    @staticmethod
    def cleanup_orphaned_records(max_age_hours=24):
        """Clean up orphaned active records (maintenance function)"""
        try:
            threshold_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            orphaned_records = AttendanceRecord.query.filter(
                AttendanceRecord.is_active == True,
                AttendanceRecord.time_in <= threshold_time
            ).all()
            
            cleaned_count = 0
            for record in orphaned_records:
                # Auto time-out with current time
                record.time_out = datetime.utcnow()
                record.is_active = False
                record.notes = (record.notes or '') + f' [Auto-timed out after {max_age_hours}h by cleanup service]'
                cleaned_count += 1
            
            if cleaned_count > 0:
                db.session.commit()
                logger.info(f"Cleaned up {cleaned_count} orphaned active records")
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'message': f'Cleaned up {cleaned_count} orphaned records'
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned records: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': 'Error during cleanup'
            }
    
    @staticmethod
    def get_attendance_state_summary(student_id=None, room_id=None):
        """Get current attendance state summary for monitoring"""
        try:
            summary = {
                'total_active_records': 0,
                'students_in_multiple_rooms': 0,
                'rooms_with_multiple_active': 0,
                'orphaned_records': 0,
                'total_students_in_system': 0
            }
            
            # Total active records
            summary['total_active_records'] = AttendanceRecord.query.filter_by(is_active=True).count()
            
            # Students in multiple rooms
            multi_room_students = db.session.query(
                AttendanceRecord.student_id,
                func.count(func.distinct(AttendanceRecord.room_id)).label('room_count')
            ).filter(
                AttendanceRecord.is_active == True
            ).group_by(AttendanceRecord.student_id).having(
                func.count(func.distinct(AttendanceRecord.room_id)) > 1
            ).all()
            
            summary['students_in_multiple_rooms'] = len(multi_room_students)
            
            # Rooms with multiple active records for same student
            multi_active_rooms = db.session.query(
                AttendanceRecord.student_id,
                AttendanceRecord.room_id,
                func.count().label('record_count')
            ).filter(
                AttendanceRecord.is_active == True
            ).group_by(
                AttendanceRecord.student_id,
                AttendanceRecord.room_id
            ).having(func.count() > 1).all()
            
            summary['rooms_with_multiple_active'] = len(multi_active_rooms)
            
            # Orphaned records
            threshold_time = datetime.utcnow() - timedelta(hours=AttendanceStateService.EXTREME_DURATION_HOURS)
            summary['orphaned_records'] = AttendanceRecord.query.filter(
                AttendanceRecord.is_active == True,
                AttendanceRecord.time_in <= threshold_time
            ).count()
            
            # Total unique students currently in system
            summary['total_students_in_system'] = db.session.query(
                func.count(func.distinct(AttendanceRecord.student_id))
            ).filter(AttendanceRecord.is_active == True).scalar() or 0
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting attendance state summary: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }