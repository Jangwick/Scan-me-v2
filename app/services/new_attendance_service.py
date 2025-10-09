"""
New Attendance Logic Service - Implements the user's requirements
"""
from datetime import datetime, timedelta
from app.models import AttendanceRecord, AttendanceSession, Student, Room
from app import db
import logging

logger = logging.getLogger(__name__)

class NewAttendanceService:
    """
    Implements the new attendance logic:
    1. First scan = time in (if session active)
    2. Second scan = time out (if same session)
    3. Sessions are isolated - no cross-session interference
    4. Grace period of 15 minutes before/after session
    5. Proper timezone handling
    """
    
    def process_session_schedule_attendance(self, student_id, session_schedule, scanned_by):
        """
        Process attendance for SessionSchedule with grace period logic:
        1. First tap: Time in (15 min grace BEFORE session = late indicator)
        2. Second tap: Show "already timed in" notification
        3. Time out: Only during 15 min grace AFTER session ends
        """
        try:
            # Get entities
            student = Student.query.get(student_id)
            room = Room.query.get(session_schedule.room_id)
            
            if not student:
                return {'success': False, 'message': 'Student not found', 'action': 'error'}
            if not room:
                return {'success': False, 'message': 'Room not found', 'action': 'error'}
            
            # Validate session timing
            timing_result = self._validate_session_timing(session_schedule)
            if not timing_result['valid']:
                return {
                    'success': False,
                    'message': timing_result['error'],
                    'action': 'error'
                }
            
            # Get current attendance record for THIS SPECIFIC SESSION ONLY (session isolation)
            current_record = AttendanceRecord.query.filter_by(
                student_id=student_id,
                schedule_session_id=session_schedule.id  # Only THIS session
            ).first()
            
            current_time = timing_result['current_time']
            session_start = timing_result['session_start']
            session_end = timing_result['session_end']
            
            # DEBUG: Write timing info to file
            import sys
            sys.stdout.flush()
            with open('debug_attendance_timing.txt', 'w') as f:
                f.write(f"=== SESSIONSCHEDULE TIMING DEBUG ===\n")
                f.write(f"Current time: {current_time} (type: {type(current_time)})\n")
                f.write(f"Session start: {session_start} (type: {type(session_start)})\n")
                f.write(f"Session end: {session_end} (type: {type(session_end)})\n")
                if hasattr(session_start, 'tzinfo'):
                    f.write(f"Session start tzinfo: {session_start.tzinfo}\n")
                if hasattr(current_time, 'tzinfo'):
                    f.write(f"Current time tzinfo: {current_time.tzinfo}\n")
                f.write(f"===================\n")
            
            # Calculate grace periods
            time_in_grace_start = session_start - timedelta(minutes=15)  # 15 mins BEFORE session
            time_out_grace_start = session_end  # Right after session ends
            time_out_grace_end = session_end + timedelta(minutes=15)  # 15 mins AFTER session
            
            # Check if in grace periods
            in_time_in_grace = time_in_grace_start <= current_time < session_start
            in_time_out_grace = time_out_grace_start <= current_time <= time_out_grace_end
            
            # FIRST TAP - TIME IN
            if current_record is None:
                # Check if we can time in
                if current_time < time_in_grace_start:
                    # Too early - before grace period
                    time_diff = time_in_grace_start - current_time
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    return {
                        'success': False,
                        'message': f'Too early to time in. Time-in opens in {hours}h {minutes}m (15 minutes before session).',
                        'action': 'error'
                    }
                elif current_time <= session_end:
                    # Can time in (grace period or active session)
                    is_late = in_time_in_grace  # Late if arrived during grace period (before session start)
                    
                    # Create attendance record (constructor doesn't accept time_in)
                    new_record = AttendanceRecord(
                        student_id=student_id,
                        room_id=session_schedule.room_id,  # Get room from session_schedule
                        session_id=None,  # Not an AttendanceSession
                        scanned_by=scanned_by,
                        is_late=is_late
                    )
                    
                    # Set SessionSchedule reference
                    new_record.schedule_session_id = session_schedule.id
                    
                    # Update time_in to current_time (not UTC)
                    new_record.time_in = current_time
                    new_record.scan_time = current_time
                    
                    db.session.add(new_record)
                    db.session.commit()
                    
                    grace_indicator = " (GRACE PERIOD - MARKED AS LATE)" if is_late else ""
                    
                    return {
                        'success': True,
                        'message': f'Time in successful{grace_indicator}! Welcome {student.get_full_name()}',
                        'action': 'time_in',
                        'is_late': is_late,
                        'in_grace_period': in_time_in_grace,
                        'time_in': current_time.isoformat()
                    }
                else:
                    # Session already ended
                    return {
                        'success': False,
                        'message': 'Cannot time in - session has ended',
                        'action': 'error'
                    }
            
            # SECOND TAP - ALREADY TIMED IN
            elif current_record.time_in and not current_record.time_out:
                # Check if in time-out grace period
                if in_time_out_grace:
                    # TIME OUT - Grace period active
                    current_record.time_out = current_time
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'message': f'Time out successful! (GRACE PERIOD) Thank you {student.get_full_name()}',
                        'action': 'time_out',
                        'in_grace_period': True,
                        'time_in': current_record.time_in.isoformat(),
                        'time_out': current_time.isoformat()
                    }
                else:
                    # NOT in grace period - just show notification
                    time_in_str = current_record.time_in.strftime("%I:%M %p")
                    
                    if current_time < session_end:
                        # Session still active
                        minutes_until_end = int((session_end - current_time).total_seconds() / 60)
                        return {
                            'success': False,
                            'message': f'You are already timed in since {time_in_str}. Time-out will be available in {minutes_until_end} minutes (15-min grace period after session ends).',
                            'action': 'already_timed_in',
                            'time_in': current_record.time_in.isoformat()
                        }
                    else:
                        # Grace period expired
                        return {
                            'success': False,
                            'message': f'You were timed in at {time_in_str}, but the 15-minute grace period for time-out has expired.',
                            'action': 'grace_expired',
                            'time_in': current_record.time_in.isoformat()
                        }
            
            # ALREADY COMPLETED
            else:
                return {
                    'success': False,
                    'message': f'You have already completed attendance for this session. Timed in at {current_record.time_in.strftime("%I:%M %p")} and timed out at {current_record.time_out.strftime("%I:%M %p")}.',
                    'action': 'complete'
                }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in process_session_schedule_attendance: {str(e)}\n{error_details}")
            
            # Write error to file for debugging
            with open('debug_error_schedule.txt', 'w') as f:
                f.write(f"Error in process_session_schedule_attendance:\n")
                f.write(f"Error message: {str(e)}\n")
                f.write(f"Full traceback:\n{error_details}\n")
            
            return {
                'success': False,
                'message': f'Error processing attendance: {str(e)}',
                'action': 'error'
            }

    def process_attendance_scan(self, student_id, room_id, session_id, scanned_by, scan_type='auto'):
        """
        Process attendance for AttendanceSession with grace period logic:
        1. First tap: Time in (15 min grace BEFORE session = late indicator)
        2. Second tap: Show "already timed in" notification  
        3. Time out: Only during 15 min grace AFTER session ends
        """
        try:
            # Get entities
            student = Student.query.get(student_id)
            room = Room.query.get(room_id)
            
            # Try to get session
            session = AttendanceSession.query.get(session_id)
            if not session:
                from app.models.session_schedule_model import SessionSchedule
                session = SessionSchedule.query.get(session_id)
            
            if not student:
                return {'success': False, 'message': 'Student not found', 'action': 'error'}
            if not room:
                return {'success': False, 'message': 'Room not found', 'action': 'error'}
            if not session:
                return {'success': False, 'message': 'Session not found', 'action': 'error'}
            
            # Validate session timing
            timing_result = self._validate_session_timing(session)
            if not timing_result['valid']:
                return {
                    'success': False,
                    'message': timing_result['error'],
                    'action': 'error'
                }
            
            # Get current attendance record for THIS SPECIFIC SESSION ONLY (session isolation)
            current_record = AttendanceRecord.query.filter_by(
                student_id=student_id,
                session_id=session_id  # Only THIS session
            ).first()
            
            current_time = timing_result['current_time']
            session_start = timing_result['session_start']
            session_end = timing_result['session_end']
            
            # Calculate grace periods
            time_in_grace_start = session_start - timedelta(minutes=15)  # 15 mins BEFORE session
            time_out_grace_start = session_end  # Right after session ends
            time_out_grace_end = session_end + timedelta(minutes=15)  # 15 mins AFTER session
            
            # Check if in grace periods
            in_time_in_grace = time_in_grace_start <= current_time < session_start
            in_time_out_grace = time_out_grace_start <= current_time <= time_out_grace_end
            
            # FIRST TAP - TIME IN
            if current_record is None:
                # Check if we can time in
                if current_time < time_in_grace_start:
                    # Too early - before grace period
                    time_diff = time_in_grace_start - current_time
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    return {
                        'success': False,
                        'message': f'Too early to time in. Time-in opens in {hours}h {minutes}m (15 minutes before session).',
                        'action': 'error'
                    }
                elif current_time <= session_end:
                    # Can time in (grace period or active session)
                    is_late = in_time_in_grace  # Late if arrived during grace period (before session start)
                    
                    # Create attendance record (constructor doesn't accept time_in)
                    new_record = AttendanceRecord(
                        student_id=student_id,
                        room_id=room_id,
                        session_id=session_id,  # Link to THIS session only
                        scanned_by=scanned_by,
                        is_late=is_late
                    )
                    
                    # Update time_in to current_time (not UTC)
                    new_record.time_in = current_time
                    new_record.scan_time = current_time
                    
                    db.session.add(new_record)
                    db.session.commit()
                    
                    grace_indicator = " (GRACE PERIOD - MARKED AS LATE)" if is_late else ""
                    
                    return {
                        'success': True,
                        'message': f'Time in successful{grace_indicator}! Welcome {student.get_full_name()}',
                        'action': 'time_in',
                        'is_late': is_late,
                        'in_grace_period': in_time_in_grace,
                        'time_in': current_time.isoformat()
                    }
                else:
                    # Session already ended
                    return {
                        'success': False,
                        'message': 'Cannot time in - session has ended',
                        'action': 'error'
                    }
            
            # SECOND TAP - ALREADY TIMED IN
            elif current_record.time_in and not current_record.time_out:
                # Check if in time-out grace period
                if in_time_out_grace:
                    # TIME OUT - Grace period active
                    current_record.time_out = current_time
                    db.session.commit()
                    
                    return {
                        'success': True,
                        'message': f'Time out successful! (GRACE PERIOD) Thank you {student.get_full_name()}',
                        'action': 'time_out',
                        'in_grace_period': True,
                        'time_in': current_record.time_in.isoformat(),
                        'time_out': current_time.isoformat()
                    }
                else:
                    # NOT in grace period - just show notification
                    time_in_str = current_record.time_in.strftime("%I:%M %p")
                    
                    if current_time < session_end:
                        # Session still active
                        minutes_until_end = int((session_end - current_time).total_seconds() / 60)
                        return {
                            'success': False,
                            'message': f'You are already timed in since {time_in_str}. Time-out will be available in {minutes_until_end} minutes (15-min grace period after session ends).',
                            'action': 'already_timed_in',
                            'time_in': current_record.time_in.isoformat()
                        }
                    else:
                        # Grace period expired
                        return {
                            'success': False,
                            'message': f'You were timed in at {time_in_str}, but the 15-minute grace period for time-out has expired.',
                            'action': 'grace_expired',
                            'time_in': current_record.time_in.isoformat()
                        }
            
            # ALREADY COMPLETED
            else:
                return {
                    'success': False,
                    'message': f'You have already completed attendance for this session. Timed in at {current_record.time_in.strftime("%I:%M %p")} and timed out at {current_record.time_out.strftime("%I:%M %p")}.',
                    'action': 'complete'
                }
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error processing attendance scan: {str(e)}\n{error_details}")
            
            # Write error to file for debugging
            with open('debug_error.txt', 'w') as f:
                f.write(f"Error in process_attendance_scan:\n")
                f.write(f"Error message: {str(e)}\n")
                f.write(f"Full traceback:\n{error_details}\n")
            
            return {
                'success': False,
                'message': 'System error occurred while processing attendance',
                'action': 'error'
            }
    
    def _validate_session_timing(self, session):
        """
        Validate session timing - DISABLED FOR FRESH START
        Always returns valid so you can implement your own logic
        """
        try:
            # Determine timezone based on session type
            if hasattr(session, 'get_session_datetime'):
                # SessionSchedule model - times are in local timezone
                current_time = datetime.now()
                session_start = session.get_session_datetime()
                session_end = session.get_session_end_datetime()
            else:
                # AttendanceSession model - ALSO uses local time (not UTC!)
                current_time = datetime.now()  # Changed from datetime.utcnow()
                if hasattr(session, 'start_datetime') and hasattr(session, 'end_datetime'):
                    session_start = session.start_datetime
                    session_end = session.end_datetime
                elif hasattr(session, 'start_time') and hasattr(session, 'end_time'):
                    session_start = session.start_time
                    session_end = session.end_time
                else:
                    return {
                        'valid': False,
                        'error': 'Invalid session model - missing time fields'
                    }
            
            # Check if session is active
            if hasattr(session, 'is_active') and not session.is_active:
                return {
                    'valid': False,
                    'error': 'Session is inactive'
                }
            
            # For SessionSchedule, check QR code active and status
            if hasattr(session, 'qr_code_active') and not session.qr_code_active:
                return {
                    'valid': False,
                    'error': 'QR code scanning is disabled for this session'
                }
            
            # ALWAYS RETURN VALID - No timing restrictions
            # You can add your own timing logic in the process methods
            return {
                'valid': True,
                'can_time_in': True,
                'can_time_out': True,
                'is_late': False,
                'in_time_in_grace': False,
                'in_time_out_grace': False,
                'session_active': True,
                'current_time': current_time,
                'session_start': session_start,
                'session_end': session_end
            }
        
        except Exception as e:
            return {
                'valid': False,
                'error': f'Session validation error: {str(e)}'
            }
    
    def _get_student_session_record(self, student_id, session_id):
        """
        Get student's attendance record for this specific session only
        Implements session isolation - only looks at records for THIS session
        Handles both AttendanceSession and SessionSchedule
        """
        # First try as AttendanceSession
        record = AttendanceRecord.query.filter_by(
            student_id=student_id,
            session_id=session_id
        ).first()
        
        if record:
            return record
        
        # Then try as SessionSchedule
        record = AttendanceRecord.query.filter_by(
            student_id=student_id,
            schedule_session_id=session_id
        ).first()
        
        return record
    
    def _process_schedule_time_in(self, student, room, session_schedule, scanned_by, timing_result):
        """Process time-in for SessionSchedule"""
        try:
            current_time = datetime.now()
            
            # Calculate if late (more than 5 minutes after start)
            session_start = session_schedule.get_session_datetime()
            is_late = current_time > session_start + timedelta(minutes=5)
            
            if is_late:
                time_diff = current_time - session_start
                minutes_late = int(time_diff.total_seconds() // 60)
                late_status = f"Late by {minutes_late} minutes"
            else:
                late_status = ""
            
            # Create new attendance record for SessionSchedule
            record = AttendanceRecord(
                student_id=student.id,
                room_id=room.id,
                scanned_by=scanned_by,
                session_id=None,  # Not an AttendanceSession
                is_late=is_late
            )
            
            # Set SessionSchedule reference
            record.schedule_session_id = session_schedule.id
            
            # Set time in
            record.time_in = current_time
            
            # Save to database
            db.session.add(record)
            db.session.commit()
            
            logger.info(f"Student {student.student_no} timed in for SessionSchedule {session_schedule.id}")
            
            message = f"Time in successful at {current_time.strftime('%I:%M:%S %p')}"
            if late_status:
                message += f" ({late_status})"
            
            return {
                'success': True,
                'message': message,
                'action': 'time_in',
                'time': current_time,
                'late': is_late
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in _process_schedule_time_in: {str(e)}")
            return {
                'success': False,
                'message': f'Error recording time in: {str(e)}',
                'action': 'error'
            }
    
    def _process_schedule_time_out(self, record, scanned_by, timing_result):
        """Process time-out for SessionSchedule"""
        try:
            current_time = datetime.now()
            
            # Update existing record
            record.time_out = current_time
            record.scanned_by = scanned_by  # Update who scanned them out
            
            # Calculate duration
            if record.time_in:
                duration = current_time - record.time_in
                duration_minutes = int(duration.total_seconds() // 60)
            else:
                duration_minutes = 0
            
            # Save to database
            db.session.commit()
            
            logger.info(f"Student {record.student_id} timed out for SessionSchedule {record.schedule_session_id}")
            
            return {
                'success': True,
                'message': f'Time out successful at {current_time.strftime("%I:%M:%S %p")} (Duration: {duration_minutes} minutes)',
                'action': 'time_out',
                'time': current_time,
                'duration_minutes': duration_minutes
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in _process_schedule_time_out: {str(e)}")
            return {
                'success': False,
                'message': f'Error recording time out: {str(e)}',
                'action': 'error'
            }

    def _process_time_in(self, student, room, session, scanned_by, timing_result):
        """Process time-in for student"""
        try:
            # Use consistent timezone handling with validation method
            if hasattr(session, 'session_date'):
                # SessionSchedule - use local time
                current_time = datetime.now()
                session_start = session.get_session_datetime() if hasattr(session, 'get_session_datetime') else None
            else:
                # AttendanceSession - use UTC time
                current_time = datetime.utcnow()
                session_start = getattr(session, 'start_time', None) or getattr(session, 'start_datetime', None)
            
            # NEW LOGIC: Student is late if they time in BEFORE official session start
            # (during the 15-minute grace period before session)
            is_late = False
            late_minutes = 0
            if session_start:
                if current_time < session_start:
                    # Timed in during grace period BEFORE session start = LATE
                    is_late = True
                    late_minutes = int((session_start - current_time).total_seconds() / 60)
                    late_status = f" (Late - arrived {late_minutes} min before start)"
                else:
                    # Timed in at or after session start = ON TIME
                    is_late = False
                    late_status = ""
            else:
                late_status = ""
            
            # Determine if this is a SessionSchedule or AttendanceSession
            is_schedule_session = hasattr(session, 'title')  # SessionSchedule has title, AttendanceSession has session_name
            
            # Create new attendance record using correct constructor
            record = AttendanceRecord(
                student_id=student.id,
                room_id=room.id,
                scanned_by=scanned_by,
                session_id=None if is_schedule_session else session.id,
                is_late=is_late
            )
            
            # Set session reference based on type
            if is_schedule_session:
                record.schedule_session_id = session.id
            else:
                record.session_id = session.id
            
            # Set additional fields manually
            record.time_in_scanned_by = scanned_by
            
            db.session.add(record)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Successfully timed in {student.get_full_name()}{late_status}',
                'action': 'time_in',
                'record_id': record.id
            }
        
        except Exception as e:
            logger.error(f"Error processing time-in: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing time-in',
                'action': 'error'
            }
    
    def _process_time_out(self, student, room, session, scanned_by, current_record, timing_result):
        """Process time-out for student"""
        try:
            # Update existing record with time-out
            current_record.time_out = datetime.utcnow()
            current_record.time_out_scanned_by = scanned_by
            current_record.is_active = False
            
            db.session.commit()
            
            # Calculate duration
            duration = current_record.get_duration()
            
            return {
                'success': True,
                'message': f'Successfully timed out {student.get_full_name()}. Duration: {duration} minutes',
                'action': 'time_out',
                'record_id': current_record.id,
                'duration': duration
            }
        
        except Exception as e:
            logger.error(f"Error processing time-out: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing time-out',
                'action': 'error'
            }