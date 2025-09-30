"""
Time Management Service for Attendance System
Handles all time calculation edge cases from QR_ATTENDANCE_EDGE_CASES.md:

- Negative Duration handling
- Extreme Duration detection  
- Midnight Crossover calculations
- Time Zone Issues
- Clock Synchronization problems
- Daylight Saving Time transitions
"""

from datetime import datetime, timedelta, timezone, time
import pytz
import logging
from typing import Tuple, Optional, Dict, Any
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

class TimeManagementService:
    """Service for handling time calculations with edge case management"""
    
    # Configuration constants
    MAX_REASONABLE_DURATION_HOURS = 18  # Maximum reasonable attendance duration
    MIN_REASONABLE_DURATION_MINUTES = 1  # Minimum reasonable attendance duration
    CLOCK_SYNC_TOLERANCE_MINUTES = 5  # Tolerance for clock synchronization issues
    DST_TRANSITION_WINDOW_HOURS = 4  # Window around DST transitions to be careful
    
    # Default timezone (can be configured)
    DEFAULT_TIMEZONE = 'UTC'
    
    @staticmethod
    def calculate_duration_safe(time_in: datetime, time_out: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Safely calculate duration with comprehensive edge case handling
        
        Args:
            time_in: Start time
            time_out: End time (if None, uses current time)
            
        Returns:
            Dict with duration info and any warnings/corrections applied
        """
        try:
            # Use current time if time_out not provided
            if time_out is None:
                time_out = datetime.utcnow()
            
            # Normalize both times to same timezone
            normalized_times = TimeManagementService._normalize_time_pair(time_in, time_out)
            norm_time_in = normalized_times['time_in']
            norm_time_out = normalized_times['time_out']
            
            # Check for negative duration (Edge Case)
            raw_duration = norm_time_out - norm_time_in
            
            corrections_applied = []
            warnings = []
            
            # Handle negative duration
            if raw_duration.total_seconds() < 0:
                corrections_applied.append("negative_duration_correction")
                warnings.append(f"Negative duration detected: {raw_duration}. Applying correction.")
                
                # Try different correction strategies
                correction_result = TimeManagementService._correct_negative_duration(
                    norm_time_in, norm_time_out
                )
                norm_time_out = correction_result['corrected_time_out']
                raw_duration = norm_time_out - norm_time_in
                corrections_applied.extend(correction_result['corrections'])
                warnings.extend(correction_result['warnings'])
            
            # Check for extremely short duration
            if raw_duration.total_seconds() < (TimeManagementService.MIN_REASONABLE_DURATION_MINUTES * 60):
                warnings.append(f"Very short duration detected: {raw_duration.total_seconds()} seconds")
            
            # Check for extremely long duration
            max_seconds = TimeManagementService.MAX_REASONABLE_DURATION_HOURS * 3600
            if raw_duration.total_seconds() > max_seconds:
                warnings.append(f"Extremely long duration detected: {raw_duration.total_seconds() / 3600:.1f} hours")
                corrections_applied.append("extreme_duration_flagged")
            
            # Handle midnight crossover
            midnight_info = TimeManagementService._analyze_midnight_crossover(norm_time_in, norm_time_out)
            if midnight_info['crosses_midnight']:
                warnings.append("Session crosses midnight boundary")
            
            # Calculate final duration in various formats
            total_seconds = int(raw_duration.total_seconds())
            total_minutes = total_seconds // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            return {
                'success': True,
                'duration_seconds': total_seconds,
                'duration_minutes': total_minutes,
                'duration_hours': hours,
                'duration_display_minutes': minutes,
                'duration_formatted': f"{hours:02d}:{minutes:02d}",
                'time_in': norm_time_in,
                'time_out': norm_time_out,
                'crosses_midnight': midnight_info['crosses_midnight'],
                'date_span_days': midnight_info['date_span_days'],
                'corrections_applied': corrections_applied,
                'warnings': warnings,
                'is_reasonable_duration': len([w for w in warnings if 'extreme' in w.lower()]) == 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating duration: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'duration_seconds': 0,
                'duration_minutes': 0,
                'warnings': [f"Duration calculation failed: {str(e)}"]
            }
    
    @staticmethod
    def _normalize_time_pair(time_in: datetime, time_out: datetime) -> Dict[str, datetime]:
        """Normalize a pair of times to handle timezone edge cases"""
        try:
            # Convert both times to UTC if they have timezone info
            norm_time_in = time_in
            norm_time_out = time_out
            
            # Handle timezone-aware datetimes
            if time_in.tzinfo is not None:
                norm_time_in = time_in.astimezone(pytz.UTC).replace(tzinfo=None)
            
            if time_out.tzinfo is not None:
                norm_time_out = time_out.astimezone(pytz.UTC).replace(tzinfo=None)
            
            return {
                'time_in': norm_time_in,
                'time_out': norm_time_out
            }
            
        except Exception as e:
            logger.error(f"Error normalizing time pair: {str(e)}")
            # Return original times if normalization fails
            return {
                'time_in': time_in,
                'time_out': time_out
            }
    
    @staticmethod
    def _correct_negative_duration(time_in: datetime, time_out: datetime) -> Dict[str, Any]:
        """Correct negative duration using various strategies"""
        corrections = []
        warnings = []
        corrected_time_out = time_out
        
        try:
            # Strategy 1: Check if times are swapped
            if abs((time_in - time_out).total_seconds()) < (TimeManagementService.CLOCK_SYNC_TOLERANCE_MINUTES * 60):
                # Times are very close - likely clock sync issue
                corrected_time_out = time_in + timedelta(minutes=TimeManagementService.MIN_REASONABLE_DURATION_MINUTES)
                corrections.append("clock_sync_correction")
                warnings.append("Applied clock synchronization correction")
            
            # Strategy 2: Check for day boundary issues
            elif time_in.date() != time_out.date() and time_out < time_in:
                # Likely crossed midnight incorrectly
                corrected_time_out = time_out + timedelta(days=1)
                corrections.append("midnight_boundary_correction")
                warnings.append("Applied midnight boundary correction")
            
            # Strategy 3: Check for DST transition
            elif TimeManagementService._is_dst_transition_period(time_in, time_out):
                # During DST transition, add an hour
                corrected_time_out = time_out + timedelta(hours=1)
                corrections.append("dst_transition_correction")
                warnings.append("Applied DST transition correction")
            
            # Strategy 4: Default correction - set to minimum duration
            else:
                corrected_time_out = time_in + timedelta(minutes=TimeManagementService.MIN_REASONABLE_DURATION_MINUTES)
                corrections.append("minimum_duration_correction")
                warnings.append("Applied minimum duration correction")
            
            return {
                'corrected_time_out': corrected_time_out,
                'corrections': corrections,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error correcting negative duration: {str(e)}")
            return {
                'corrected_time_out': time_in + timedelta(minutes=1),
                'corrections': ['error_fallback_correction'],
                'warnings': [f"Error during correction, applied fallback: {str(e)}"]
            }
    
    @staticmethod
    def _is_dst_transition_period(time_in: datetime, time_out: datetime) -> bool:
        """Check if times fall within DST transition period"""
        try:
            # For simplicity, check if we're in March (spring forward) or November (fall back)
            # This is a simplified check - real implementation would need timezone-specific logic
            transition_months = [3, 11]  # March and November for most regions
            
            return (time_in.month in transition_months or 
                    time_out.month in transition_months)
            
        except Exception as e:
            logger.error(f"Error checking DST transition: {str(e)}")
            return False
    
    @staticmethod
    def _analyze_midnight_crossover(time_in: datetime, time_out: datetime) -> Dict[str, Any]:
        """Analyze if session crosses midnight and handle edge cases"""
        try:
            crosses_midnight = time_in.date() != time_out.date()
            date_span_days = (time_out.date() - time_in.date()).days + 1
            
            # Additional analysis for complex midnight scenarios
            analysis = {
                'crosses_midnight': crosses_midnight,
                'date_span_days': date_span_days,
                'time_in_date': time_in.date(),
                'time_out_date': time_out.date(),
                'is_multi_day': date_span_days > 1
            }
            
            # Handle multi-day sessions (likely an error)
            if date_span_days > 2:  # More than 1 day span
                analysis['warning'] = f"Session spans {date_span_days} days - possible data error"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing midnight crossover: {str(e)}")
            return {
                'crosses_midnight': False,
                'date_span_days': 1,
                'error': str(e)
            }
    
    @staticmethod
    def validate_session_times(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Validate session start and end times for edge cases"""
        try:
            validation_result = {
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Check for negative duration
            if end_time <= start_time:
                validation_result['valid'] = False
                validation_result['errors'].append("End time must be after start time")
            
            # Check for reasonable duration
            duration = end_time - start_time
            duration_hours = duration.total_seconds() / 3600
            
            if duration_hours < 0.5:  # Less than 30 minutes
                validation_result['warnings'].append("Session duration is very short (less than 30 minutes)")
            
            if duration_hours > 12:  # More than 12 hours
                validation_result['warnings'].append("Session duration is very long (more than 12 hours)")
            
            # Check for midnight crossover
            if start_time.date() != end_time.date():
                validation_result['warnings'].append("Session crosses midnight - ensure timezone handling is correct")
            
            # Check for weekend sessions
            if start_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                validation_result['warnings'].append("Session scheduled on weekend")
            
            # Check for late night sessions
            if start_time.hour >= 22 or start_time.hour <= 5:
                validation_result['warnings'].append("Session scheduled during late night/early morning hours")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating session times: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    @staticmethod
    def calculate_late_arrival(session_start: datetime, arrival_time: datetime, 
                             grace_period_minutes: int = 10) -> Dict[str, Any]:
        """Calculate late arrival with grace period and edge case handling"""
        try:
            # Normalize times
            normalized = TimeManagementService._normalize_time_pair(session_start, arrival_time)
            norm_start = normalized['time_in']
            norm_arrival = normalized['time_out']
            
            # Calculate grace period end
            grace_period_end = norm_start + timedelta(minutes=grace_period_minutes)
            
            # Calculate lateness
            is_late = norm_arrival > grace_period_end
            lateness_minutes = 0
            
            if is_late:
                lateness_duration = norm_arrival - grace_period_end
                lateness_minutes = int(lateness_duration.total_seconds() / 60)
            
            # Edge case: Arrival before session start
            early_arrival = False
            early_minutes = 0
            if norm_arrival < norm_start:
                early_arrival = True
                early_duration = norm_start - norm_arrival
                early_minutes = int(early_duration.total_seconds() / 60)
            
            # Grace period boundary analysis
            at_grace_boundary = abs((norm_arrival - grace_period_end).total_seconds()) <= 30  # Within 30 seconds
            
            return {
                'is_late': is_late,
                'is_early': early_arrival,
                'lateness_minutes': lateness_minutes,
                'early_minutes': early_minutes,
                'at_grace_boundary': at_grace_boundary,
                'session_start': norm_start,
                'arrival_time': norm_arrival,
                'grace_period_end': grace_period_end,
                'grace_period_minutes': grace_period_minutes
            }
            
        except Exception as e:
            logger.error(f"Error calculating late arrival: {str(e)}")
            return {
                'is_late': False,
                'is_early': False,
                'lateness_minutes': 0,
                'early_minutes': 0,
                'error': str(e)
            }
    
    @staticmethod
    def detect_clock_synchronization_issues(times_list: list) -> Dict[str, Any]:
        """Detect potential clock synchronization issues across multiple times"""
        try:
            if len(times_list) < 2:
                return {'has_issues': False, 'message': 'Insufficient data for analysis'}
            
            # Sort times
            sorted_times = sorted(times_list)
            
            issues = []
            
            # Check for times that are too close together (rapid scans)
            for i in range(1, len(sorted_times)):
                time_diff = (sorted_times[i] - sorted_times[i-1]).total_seconds()
                if time_diff < 1:  # Less than 1 second apart
                    issues.append(f"Extremely rapid scans detected: {time_diff} seconds apart")
            
            # Check for large gaps that might indicate clock issues
            for i in range(1, len(sorted_times)):
                time_diff = (sorted_times[i] - sorted_times[i-1]).total_seconds()
                if time_diff > 3600:  # More than 1 hour gap
                    issues.append(f"Large time gap detected: {time_diff/3600:.1f} hours")
            
            # Check for future times (compared to now)
            now = datetime.utcnow()
            future_times = [t for t in times_list if t > now + timedelta(minutes=5)]
            if future_times:
                issues.append(f"Future timestamps detected: {len(future_times)} times in the future")
            
            return {
                'has_issues': len(issues) > 0,
                'issues': issues,
                'analyzed_count': len(times_list),
                'time_span_hours': (max(times_list) - min(times_list)).total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"Error detecting clock sync issues: {str(e)}")
            return {
                'has_issues': True,
                'issues': [f"Analysis error: {str(e)}"],
                'error': str(e)
            }
    
    @staticmethod
    def get_current_time_info() -> Dict[str, Any]:
        """Get comprehensive current time information for debugging"""
        try:
            now_utc = datetime.utcnow()
            now_local = datetime.now()
            
            return {
                'utc_time': now_utc.isoformat(),
                'local_time': now_local.isoformat(),
                'timezone_offset_hours': (now_local - now_utc).total_seconds() / 3600,
                'is_dst': time.daylight and time.localtime().tm_isdst,
                'system_timezone': str(now_local.astimezone().tzinfo),
                'timestamp_unix': now_utc.timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error getting time info: {str(e)}")
            return {
                'error': str(e),
                'utc_time': datetime.utcnow().isoformat()
            }


class SessionTimeValidator:
    """Specialized validator for session time management"""
    
    @staticmethod
    def validate_session_scheduling(room_id: int, start_time: datetime, end_time: datetime,
                                  session_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate session scheduling for conflicts and edge cases"""
        try:
            from app.models.attendance_model import AttendanceSession
            
            validation_result = {
                'valid': True,
                'conflicts': [],
                'warnings': []
            }
            
            # Basic time validation
            basic_validation = TimeManagementService.validate_session_times(start_time, end_time)
            if not basic_validation['valid']:
                validation_result['valid'] = False
                validation_result['conflicts'].extend(basic_validation['errors'])
            validation_result['warnings'].extend(basic_validation['warnings'])
            
            # Check for overlapping sessions in the same room
            overlap_query = AttendanceSession.query.filter(
                AttendanceSession.room_id == room_id,
                AttendanceSession.is_active == True,
                or_(
                    # New session starts during existing session
                    and_(
                        AttendanceSession.start_time <= start_time,
                        AttendanceSession.end_time > start_time
                    ),
                    # New session ends during existing session  
                    and_(
                        AttendanceSession.start_time < end_time,
                        AttendanceSession.end_time >= end_time
                    ),
                    # New session completely contains existing session
                    and_(
                        AttendanceSession.start_time >= start_time,
                        AttendanceSession.end_time <= end_time
                    ),
                    # Existing session completely contains new session
                    and_(
                        AttendanceSession.start_time <= start_time,
                        AttendanceSession.end_time >= end_time
                    )
                )
            )
            
            # Exclude current session if editing
            if session_id:
                overlap_query = overlap_query.filter(AttendanceSession.id != session_id)
            
            conflicting_sessions = overlap_query.all()
            
            if conflicting_sessions:
                validation_result['valid'] = False
                for session in conflicting_sessions:
                    validation_result['conflicts'].append(
                        f"Overlaps with session '{session.session_name}' "
                        f"({session.start_time} - {session.end_time})"
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating session scheduling: {str(e)}")
            return {
                'valid': False,
                'conflicts': [f"Validation error: {str(e)}"],
                'warnings': []
            }