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
    RAPID_SCAN_THRESHOLD = 2  # seconds (reduced for grace period scenarios)
    DUPLICATE_SCAN_WINDOW = 300  # 5 minutes in seconds
    EXTREME_DURATION_HOURS = 24  # hours
    MAX_CONCURRENT_ACTIVE_RECORDS = 1  # per student per room
    GRACE_PERIOD_MINUTES = 10  # late arrival grace period
    
    @staticmethod
    def process_attendance_scan_new_logic(student_id, room_id, session_id, scanned_by, scan_type='auto', 
                              user_agent=None, ip_address=None):
        """
        NEW ATTENDANCE LOGIC - Use this instead of the old method
        1. First scan = time in (if session active)
        2. Second scan = time out (if same session)
        3. Sessions are isolated - no cross-session interference
        4. Grace period of 15 minutes before/after session
        """
        try:
            # Import and use the new service
            from app.services.new_attendance_service import NewAttendanceService
            from app.models.session_schedule_model import SessionSchedule
            
            new_service = NewAttendanceService()
            
            # Check if this is a SessionSchedule (new model) or AttendanceSession (legacy)
            session = SessionSchedule.query.get(session_id)
            
            if session:
                # Use the SessionSchedule-specific method with custom flow
                result = new_service.process_session_schedule_attendance(
                    student_id=student_id,
                    session_schedule=session,
                    scanned_by=scanned_by
                )
            else:
                # Fall back to legacy AttendanceSession processing
                result = new_service.process_attendance_scan(
                    student_id=student_id,
                    room_id=room_id,
                    session_id=session_id,
                    scanned_by=scanned_by,
                    scan_type=scan_type
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in new attendance logic: {str(e)}")
            return {
                'success': False,
                'message': 'System error occurred while processing attendance',
                'action': 'error',
                'error_code': 'SYSTEM_ERROR'
            }

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
            
            # Get current state first
            state_analysis = AttendanceStateService._analyze_current_state(
                student_id, room_id, session_id
            )
            
            # Early session validation for post-grace-period scenarios
            if session:
                session_validation = AttendanceStateService._validate_session_timing(
                    session, scan_type, state_analysis
                )
                if not session_validation['valid']:
                    return session_validation
            
            # Check for rapid sequential scans
            # But allow legitimate time-in → time-out transitions
            rapid_scan_check = AttendanceStateService._check_rapid_sequential_scans(
                student_id, room_id, session_id, state_analysis
            )
            if not rapid_scan_check['allowed']:
                return rapid_scan_check
            
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
    def _validate_session_timing(session, scan_type, state_analysis):
        """Validate session timing for all scan types, especially post-grace-period scenarios"""
        try:
            now = datetime.now()  # Use local time instead of UTC
            
            # Handle different session model types
            if hasattr(session, 'session_date'):
                # SessionSchedule model - combine date and time
                session_end_datetime = datetime.combine(session.session_date, session.end_time)
            else:
                # AttendanceSession model - end_time is already a datetime
                session_end_datetime = session.end_time
            
            # Check if session has ended and grace period has expired
            if now > session_end_datetime:
                grace_period = timedelta(minutes=15)
                grace_end_time = session_end_datetime + grace_period
                
                if now > grace_end_time:
                    # Grace period has completely expired
                    grace_expired_minutes = int((now - grace_end_time).total_seconds() / 60)
                    
                    # For auto scans, determine what the user was likely trying to do
                    if scan_type == 'auto':
                        current_status = state_analysis['current_status']
                        if current_status == 'in_room':
                            action_attempt = "time out"
                        else:
                            action_attempt = "scan in"
                    elif scan_type == 'time_in':
                        action_attempt = "time in"
                    else:  # time_out
                        action_attempt = "time out"
                    
                    # Format end time appropriately based on session model
                    if hasattr(session, 'session_date'):
                        end_time_str = session.end_time.strftime("%I:%M %p")
                    else:
                        end_time_str = session.end_time.strftime("%I:%M %p")
                    
                    return {
                        'valid': False,
                        'success': False,
                        'message': f'Cannot {action_attempt} - session has ended. The 15-minute grace period expired {grace_expired_minutes} minutes ago. Session ended at {end_time_str}.',
                        'error_code': 'SESSION_GRACE_PERIOD_EXPIRED',
                        'action': 'error'
                    }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating session timing: {str(e)}")
            return {
                'valid': False,
                'success': False,
                'message': 'Session validation error occurred',
                'error_code': 'SESSION_VALIDATION_ERROR',
                'action': 'error'
            }

    @staticmethod
    def _check_rapid_sequential_scans(student_id, room_id, session_id, state_analysis):
        """Check for rapid sequential scans (Edge Case: Double Scanning)"""
        try:
            threshold_time = datetime.utcnow() - timedelta(seconds=AttendanceStateService.RAPID_SCAN_THRESHOLD)
            
            # SESSION-SPECIFIC: Only check recent scans within this specific session
            recent_scan = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.session_id == session_id,  # KEY: Session-specific check
                AttendanceRecord.time_in >= threshold_time
            ).first()
            
            if recent_scan:
                # Check if this would be a legitimate state transition
                current_status = state_analysis['current_status']
                
                # Allow time-in → time-out transitions (legitimate flow)
                # Only block same-action rapid scans (time-in after time-in, time-out after time-out)
                if current_status == 'in_room':
                    # Student is currently in room, so this would be a time-out (allowed)
                    return {'allowed': True}
                elif current_status == 'not_in_room':
                    # Student is not in room, so this would be a time-in
                    # Only block if recent scan was also a time-in (i.e., recent scan was successful)
                    if recent_scan.is_active:
                        # Recent scan was successful time-in, this would be duplicate time-in
                        return {
                            'allowed': False,
                            'success': False,
                            'message': f'Please wait {AttendanceStateService.RAPID_SCAN_THRESHOLD} seconds between scans',
                            'error_code': 'RAPID_SCAN_DETECTED',
                            'action': 'rate_limited'
                        }
                    else:
                        # Recent scan was failed/timed-out, allow retry
                        return {'allowed': True}
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Error checking rapid scans: {str(e)}")
            return {'allowed': True}  # Allow scan if check fails
    
    @staticmethod
    def _analyze_current_state(student_id, room_id, session_id):
        """Analyze current attendance state for the student"""
        try:
            # STRICT SESSION ISOLATION: Only look at records for THIS specific session
            # This ensures different sessions/subjects don't interfere with each other
            
            # Get active records for student in this specific session only
            active_records = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.session_id == session_id,  # KEY: Filter by specific session
                AttendanceRecord.is_active == True
            ).all()
            
            # Get active records for student in OTHER sessions (different rooms or different sessions)
            # This helps detect if student is active elsewhere but doesn't interfere with current session logic
            other_session_active = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.is_active == True,
                db.or_(
                    AttendanceRecord.room_id != room_id,
                    AttendanceRecord.session_id != session_id
                )
            ).all()
            
            # Check for orphaned records (only in current session to avoid cross-session cleanup)
            orphaned_records = AttendanceStateService._detect_orphaned_records(student_id, session_id)
            
            # Get recent scans in duplicate window (SESSION-SPECIFIC)
            duplicate_window = datetime.utcnow() - timedelta(seconds=AttendanceStateService.DUPLICATE_SCAN_WINDOW)
            recent_scans = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.room_id == room_id,
                AttendanceRecord.session_id == session_id,  # KEY: Only recent scans in this session
                AttendanceRecord.time_in >= duplicate_window
            ).all()
            
            return {
                'active_records_this_room': active_records,
                'active_records_other_sessions': other_session_active,  # Renamed for clarity
                'orphaned_records': orphaned_records,
                'recent_scans': recent_scans,
                'has_multiple_active': len(active_records) > 1,
                'is_in_other_sessions': len(other_session_active) > 0,  # Renamed for clarity
                'current_status': AttendanceStateService._determine_current_status(active_records)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing current state: {str(e)}")
            return {
                'active_records_this_room': [],
                'active_records_other_sessions': [],  # Updated name
                'orphaned_records': [],
                'recent_scans': [],
                'has_multiple_active': False,
                'is_in_other_sessions': False,  # Updated name
                'current_status': 'unknown'
            }
    
    @staticmethod
    def _detect_orphaned_records(student_id, session_id=None):
        """Detect orphaned active records (Edge Case: Missing Time-Out)"""
        try:
            # Find active records older than extreme duration threshold
            threshold_time = datetime.utcnow() - timedelta(hours=AttendanceStateService.EXTREME_DURATION_HOURS)
            
            query = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.is_active == True,
                AttendanceRecord.time_in <= threshold_time
            )
            
            # If session_id provided, only check within that session to avoid cross-session interference
            if session_id:
                query = query.filter(AttendanceRecord.session_id == session_id)
            
            orphaned = query.all()
            
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
            
            # Handle student in multiple sessions edge case
            # NOTE: With session isolation, being in other sessions should NOT be a problem
            # Each session should be completely independent
            if state_analysis['is_in_other_sessions']:
                # Log for informational purposes only - do NOT treat as error
                logger.info(f"Info: {student.get_full_name()} has active records in other sessions/rooms (session isolation allows this)")
                # Continue with processing - this is normal and allowed
            
            # Determine action based on scan type and state
            if scan_type == 'time_out':
                if current_status == 'not_in_room':
                    return {
                        'success': False,
                        'message': f'{student.get_full_name()} is not currently in this room',
                        'error_code': 'NOT_IN_ROOM',
                        'action': 'error'
                    }
                
                # Check if session is in grace period (time-out only allowed after session ends)
                if session:
                    now = datetime.now()
                    
                    # Handle different session types
                    if hasattr(session, 'session_date') and hasattr(session, 'end_time'):
                        # SessionSchedule model
                        session_end_datetime = datetime.combine(session.session_date, session.end_time)
                    elif hasattr(session, 'date') and hasattr(session, 'end_time'):
                        # AttendanceSession model
                        session_end_datetime = datetime.combine(session.date, session.end_time)
                    else:
                        # Unknown session type - allow time out
                        return {'action': 'time_out'}
                    
                    if now < session_end_datetime:
                        return {
                            'success': False,
                            'message': 'You can only time out after the session ends.',
                            'error_code': 'SESSION_STILL_ACTIVE',
                            'action': 'error'
                        }
                    
                    # Check if grace period expired
                    grace_period = timedelta(minutes=15)
                    grace_end_time = session_end_datetime + grace_period
                    
                    if now > grace_end_time:
                        return {
                            'success': False,
                            'message': 'Grace period for time-out has expired',
                            'error_code': 'GRACE_PERIOD_EXPIRED',
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
                # Custom flow: First scan = time in, second scan = notification
                if current_status == 'not_in_room':
                    return {'action': 'time_in'}
                elif current_status == 'in_room':
                    # Check if session is in grace period (after session ends)
                    if session:
                        now = datetime.now()
                        
                        # Handle different session types
                        if hasattr(session, 'session_date') and hasattr(session, 'end_time'):
                            # SessionSchedule model
                            session_end_datetime = datetime.combine(session.session_date, session.end_time)
                        elif hasattr(session, 'date') and hasattr(session, 'end_time'):
                            # AttendanceSession model
                            session_end_datetime = datetime.combine(session.date, session.end_time)
                        else:
                            # Unknown session type - show already timed in
                            return {
                                'success': False,
                                'message': f'{student.get_full_name()} is already timed in.',
                                'error_code': 'ALREADY_TIMED_IN',
                                'action': 'duplicate'
                            }
                        
                        # Time-out only allowed during grace period (after session ends)
                        if now < session_end_datetime:
                            # Session still active - show "already timed in" notification
                            return {
                                'success': False,
                                'message': f'{student.get_full_name()} is already timed in. You can only time out after the session ends.',
                                'error_code': 'ALREADY_TIMED_IN',
                                'action': 'duplicate'
                            }
                        else:
                            # Session ended - check if still within grace period
                            grace_period = timedelta(minutes=15)
                            grace_end_time = session_end_datetime + grace_period
                            
                            if now > grace_end_time:
                                return {
                                    'success': False,
                                    'message': 'Grace period for time-out has expired',
                                    'error_code': 'GRACE_PERIOD_EXPIRED',
                                    'action': 'error'
                                }
                            return {'action': 'time_out'}
                    else:
                        # No session context - show already timed in notification
                        return {
                            'success': False,
                            'message': f'{student.get_full_name()} is already timed in.',
                            'error_code': 'ALREADY_TIMED_IN',
                            'action': 'duplicate'
                        }
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
            # Use local time instead of UTC to match session times
            now = datetime.now()
            
            # Security Check: Prevent time-in outside session hours
            if session:
                # Handle different session model types
                if hasattr(session, 'session_date'):
                    # SessionSchedule model - combine date and time
                    session_start_datetime = datetime.combine(session.session_date, session.start_time)
                    session_end_datetime = datetime.combine(session.session_date, session.end_time)
                    start_time_str = session.start_time.strftime("%I:%M %p")
                    end_time_str = session.end_time.strftime("%I:%M %p")
                else:
                    # AttendanceSession model - times are already datetime objects
                    session_start_datetime = session.start_time
                    session_end_datetime = session.end_time
                    start_time_str = session.start_time.strftime("%I:%M %p")
                    end_time_str = session.end_time.strftime("%I:%M %p")
                
                if now < session_start_datetime:
                    # Session hasn't started yet
                    minutes_until_start = int((session_start_datetime - now).total_seconds() / 60)
                    hours_until_start = minutes_until_start // 60
                    mins_until_start = minutes_until_start % 60
                    
                    time_until_msg = f"{hours_until_start}h {mins_until_start}m" if hours_until_start > 0 else f"{minutes_until_start}m"
                    
                    return {
                        'success': False,
                        'message': f'Cannot time in before session starts. Session starts in {time_until_msg} at {start_time_str}.',
                        'error_code': 'SESSION_NOT_STARTED',
                        'action': 'error'
                    }
                elif now > session_end_datetime:
                    # Check if we're within the 15-minute grace period
                    grace_period = timedelta(minutes=15)
                    grace_end_time = session_end_datetime + grace_period
                    
                    if now > grace_end_time:
                        # Grace period has expired - session is completely over
                        grace_expired_minutes = int((now - grace_end_time).total_seconds() / 60)
                        return {
                            'success': False,
                            'message': f'Session has ended. The 15-minute grace period expired {grace_expired_minutes} minutes ago. Session ended at {end_time_str}.',
                            'error_code': 'SESSION_GRACE_PERIOD_EXPIRED',
                            'action': 'error'
                        }
                    else:
                        # Within grace period - session has ended but time-ins are still blocked
                        return {
                            'success': False,
                            'message': f'Cannot time in after session has ended. Session ended at {end_time_str}.',
                            'error_code': 'SESSION_ENDED',
                            'action': 'error'
                        }
            
            # Check for recent duplicate scans
            # Only block if it's the SAME action type (prevent rapid duplicate time-ins or time-outs)
            recent_scans = state_analysis['recent_scans']
            if recent_scans:
                most_recent = max(recent_scans, key=lambda r: r.time_in)
                time_since_last = (now - most_recent.time_in).total_seconds()
                
                # Only check for duplicates if this would be another time-in
                # (Don't block time-out after a recent time-in - that's legitimate!)
                current_status = state_analysis['current_status']
                if (time_since_last < AttendanceStateService.DUPLICATE_SCAN_WINDOW and 
                    current_status == 'not_in_room'):  # This would be a time-in
                    return {
                        'success': False,
                        'message': f'{student.get_full_name()} has a recent time-in scan in this room',
                        'error_code': 'RECENT_DUPLICATE_TIME_IN',
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
            
            # Security Check: Prevent time-out before session ends (with 15-minute grace period)
            # EXCEPTION: Allow immediate time-out if student timed in before session started
            if session:
                now = datetime.now()  # Use local time instead of UTC
                
                # Handle different session model types
                if hasattr(session, 'session_date'):
                    # SessionSchedule model - combine date and time
                    session_start_datetime = datetime.combine(session.session_date, session.start_time)
                    session_end_datetime = datetime.combine(session.session_date, session.end_time)
                    end_time_str = session.end_time.strftime("%I:%M %p")
                else:
                    # AttendanceSession model - times are already datetime objects
                    session_start_datetime = session.start_time
                    session_end_datetime = session.end_time
                    end_time_str = session.end_time.strftime("%I:%M %p")
                
                grace_period = timedelta(minutes=15)
                grace_end_time = session_end_datetime + grace_period
                
                # Check if student timed in before session started
                timed_in_before_session = active_record.time_in < session_start_datetime
                
                if now > grace_end_time:
                    # Grace period expired - prevent late time-out
                    grace_expired_minutes = int((now - grace_end_time).total_seconds() / 60)
                    return {
                        'success': False,
                        'message': f'Cannot time out after grace period has expired. Grace period ended {grace_expired_minutes} minutes ago.',
                        'error_code': 'GRACE_PERIOD_EXPIRED',
                        'action': 'error'
                    }
                # Allow time-out during session or within grace period
                
            # Handle time zone consistency
            now = datetime.now()  # Use local time instead of UTC
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
            
            # Check if this is during grace period for enhanced messaging
            grace_message = ""
            if session:
                grace_period = timedelta(minutes=15)
                grace_end_time = session.end_time + grace_period
                if session.end_time <= normalized_time <= grace_end_time:
                    grace_remaining = int((grace_end_time - normalized_time).total_seconds() / 60)
                    grace_message = f" (Grace period - {grace_remaining} minutes remaining)"
            
            # Log the time-out
            logger.info(f"Time-out: Student {student.id} from room {room.id} at {normalized_time}, duration: {duration} minutes")
            
            return {
                'success': True,
                'message': f'Successfully timed out {student.get_full_name()}. Duration: {duration} minutes{grace_message}',
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
    def get_attendance_state_summary(student_id=None, room_id=None, session_id=None):
        """Get current attendance state summary for monitoring (session-aware)"""
        try:
            summary = {
                'total_active_records': 0,
                'students_in_multiple_sessions': 0,
                'rooms_with_multiple_active': 0,
                'orphaned_records': 0,
                'total_students_in_system': 0,
                'session_specific': session_id is not None
            }
            
            # Build base query with session isolation
            base_query = AttendanceRecord.query.filter_by(is_active=True)
            
            if session_id:
                base_query = base_query.filter_by(session_id=session_id)
            if room_id:
                base_query = base_query.filter_by(room_id=room_id)
            if student_id:
                base_query = base_query.filter_by(student_id=student_id)
            
            # Total active records (session-filtered)
            summary['total_active_records'] = base_query.count()
            
            # Students in multiple sessions/rooms (session-aware)
            if session_id:
                # For specific session, check for students active in other sessions
                multi_session_students = db.session.query(
                    AttendanceRecord.student_id,
                    func.count(func.distinct(AttendanceRecord.session_id)).label('session_count')
                ).filter(
                    AttendanceRecord.is_active == True,
                    AttendanceRecord.student_id.in_(
                        base_query.with_entities(AttendanceRecord.student_id)
                    )
                ).group_by(AttendanceRecord.student_id).having(
                    func.count(func.distinct(AttendanceRecord.session_id)) > 1
                ).all()
                
                summary['students_in_multiple_sessions'] = len(multi_session_students)
            else:
                # Global view - students in multiple rooms
                multi_room_students = db.session.query(
                    AttendanceRecord.student_id,
                    func.count(func.distinct(AttendanceRecord.room_id)).label('room_count')
                ).filter(
                    AttendanceRecord.is_active == True
                ).group_by(AttendanceRecord.student_id).having(
                    func.count(func.distinct(AttendanceRecord.room_id)) > 1
                ).all()
                
                summary['students_in_multiple_sessions'] = len(multi_room_students)
            
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