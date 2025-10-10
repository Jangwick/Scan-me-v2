# Late Attendance Badge Feature

## Overview
Added visual indicators in the Recent Scans section to mark students as "LATE" if they did not time in during the grace period (15 minutes before the active session starts).

## Grace Period Logic

### Time-In Window
- **15 minutes before session start**: Grace period begins - Students can arrive early
- **During grace period (15 min before)**: Students time in **ON TIME** ✅
- **After session starts**: Students time in **LATE** ⚠️

### Late Status Criteria
A student is marked as **LATE** if they time in AFTER the session has officially started.

Example:
- Session starts: 8:00 AM
- Grace period: 7:45 AM - 7:59:59 AM
- Student arrives at 7:50 AM → **ON TIME** ✅ (Grace period)
- Student arrives at 8:00 AM → **LATE** ⚠️ (Session started)
- Student arrives at 8:15 AM → **LATE** ⚠️ (Session started)

## Changes Made

### 1. Backend Changes

#### app/routes/professor_routes.py

**A. Updated `get_session_stats()` - Added is_late to recent_scans**
```python
recent_scans.append({
    'student_id': student.id,
    'name': f"{student.first_name} {student.last_name}",
    'type': scan_type,
    'time': scan_time.isoformat() if scan_time else None,
    'is_late': record.is_late  # Include late status
})
```
*Applied to both SessionSchedule and legacy AttendanceSession sections*

**B. Updated `process_session_scan()` - Include is_late in response**
```python
return jsonify({
    'success': True,
    'message': result['message'],
    'action': result['action'],
    'is_late': result.get('is_late', False),  # Include late status
    'student': {
        'id': student.id,
        'name': student.get_full_name(),
        'student_no': student.student_no
    }
})
```

### 2. Frontend Changes

#### app/templates/professor/session_scanner.html

**A. Added CSS for Late Badge (Lines ~835-870)**
```css
.late-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 1px solid #fbbf24;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    color: #78350f;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 2px 4px -1px rgba(251, 191, 36, 0.2);
    animation: latePulse 2s infinite;
}

.late-badge i {
    font-size: 0.7rem;
    color: #d97706;
}

@keyframes latePulse {
    0%, 100% {
        box-shadow: 0 2px 4px -1px rgba(251, 191, 36, 0.2);
    }
    50% {
        box-shadow: 0 3px 8px -1px rgba(251, 191, 36, 0.4);
    }
}
```

**B. Updated `updateRecentScansDisplay()` - Display late badge**
```javascript
container.innerHTML = sessionStats.scans.map(scan => `
    <div class="scan-item" data-scan-type="${scan.type === 'time_in' ? 'entry' : 'exit'}">
        <div class="scan-avatar">
            ${scan.name.charAt(0).toUpperCase()}
        </div>
        <div class="scan-details">
            <div class="scan-name">
                ${scan.name}
                ${scan.is_late && scan.type === 'time_in' ? '<span class="late-badge"><i class="fas fa-exclamation-circle"></i> LATE</span>' : ''}
            </div>
            <div class="scan-time">
                ${scan.type === 'time_in' ? 'Entered' : 'Exited'} at ${scan.time.toLocaleTimeString()}
            </div>
        </div>
    </div>
`).join('');
```

**C. Updated `loadSessionStatistics()` - Load is_late from server**
```javascript
sessionStats.scans = stats.recent_scans.map(scan => ({
    student_id: scan.student_id,
    name: scan.name,
    type: scan.type,
    time: new Date(scan.time),
    is_late: scan.is_late || false  // Include late status
}));
```

**D. Updated `addRecentScan()` - Accept is_late parameter**
```javascript
function addRecentScan(studentName, scanType, isLate = false) {
    const scanItem = {
        name: studentName,
        type: scanType,
        time: new Date(),
        is_late: isLate
    };
    // ... rest of function
}
```

**E. Updated `processQRCode()` - Pass is_late when adding scan**
```javascript
if (result.success) {
    showMessage(result.message, 'success');
    addRecentScan(result.student.name, result.action, result.is_late || false);
    updateSessionStats(result.student.id, result.action);
}
```

## Visual Design

### Late Badge Appearance
- **Background**: Yellow gradient (#fef3c7 → #fde68a)
- **Border**: Golden yellow (#fbbf24)
- **Text Color**: Dark brown (#78350f)
- **Icon**: Exclamation circle (⚠️) in orange (#d97706)
- **Animation**: Subtle pulsing effect every 2 seconds
- **Size**: Compact, inline with student name

### Example Display
```
Recent Scans
┌─────────────────────────────────────┐
│ J  Juan Dela Cruz  [⚠️ LATE]       │
│    Entered at 7:50:23 AM            │
├─────────────────────────────────────┤
│ M  Maria Santos                     │
│    Entered at 8:00:15 AM            │
└─────────────────────────────────────┘
```

## Data Flow

### Real-time Scan
1. Student scans QR code
2. Backend checks if time_in is during grace period
3. Sets `is_late = True` if in grace period
4. Returns `is_late` in response
5. Frontend displays "LATE" badge immediately

### Page Refresh / Load
1. Frontend calls `loadSessionStatistics()`
2. Backend fetches all attendance records
3. Each record includes `is_late` field from database
4. Frontend displays "LATE" badge for late scans

### Auto-Refresh (Every 10 seconds)
1. Periodically syncs with database
2. Updates recent scans with latest data
3. Late badges appear/persist correctly

## Benefits

✅ **Clear Visual Feedback** - Professors instantly see which students arrived late
✅ **Persistent Data** - Late status stored in database, survives page refresh
✅ **Professional Design** - Animated badge draws attention without being obtrusive
✅ **Accurate Tracking** - Only marks time-in scans as late (not time-out)
✅ **Grace Period Clarity** - Makes the 15-minute grace period concept visible

## Notes

- **Only time-in scans show late badge** - Time-out scans never show "LATE"
- **Database-driven** - `is_late` stored in `AttendanceRecord.is_late` column
- **Grace period = 15 minutes** - Configurable in service layer if needed
- **Color-coded** - Yellow/orange stands out from green (entry) and red (exit)
