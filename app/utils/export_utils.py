"""
Export Utilities for ScanMe System
Handles data export to various formats (Excel, CSV, PDF)
"""

import pandas as pd
from datetime import datetime, date
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

def export_attendance_to_excel(attendance_data, filename=None):
    """
    Export attendance data to Excel file
    Args:
        attendance_data (list): List of attendance record dictionaries
        filename (str): Output filename
    Returns:
        str: Path to created file
    """
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_report_{timestamp}.xlsx"
        
        # Convert to DataFrame
        df = pd.DataFrame(attendance_data)
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Report"
        
        # Add header
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        # Write data
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # Format header
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min((max_length + 2) * 1.2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save file
        output_path = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        wb.save(output_path)
        
        return output_path
        
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return None

def export_attendance_to_csv(attendance_data, filename=None):
    """
    Export attendance data to CSV file
    Args:
        attendance_data (list): List of attendance record dictionaries
        filename (str): Output filename
    Returns:
        str: Path to created file
    """
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_report_{timestamp}.csv"
        
        output_path = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        
        if not attendance_data:
            return None
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            if attendance_data:
                fieldnames = attendance_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(attendance_data)
        
        return output_path
        
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return None

def export_attendance_to_pdf(attendance_data, title="Attendance Report", filename=None):
    """
    Export attendance data to PDF file
    Args:
        attendance_data (list): List of attendance record dictionaries
        title (str): Report title
        filename (str): Output filename
    Returns:
        str: Path to created file
    """
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_report_{timestamp}.pdf"
        
        output_path = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Add title
        title_para = Paragraph(title, title_style)
        elements.append(title_para)
        
        # Add generation date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            spaceAfter=20
        )
        date_para = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
        elements.append(date_para)
        
        if attendance_data:
            # Prepare table data
            headers = list(attendance_data[0].keys())
            table_data = [headers]
            
            for record in attendance_data:
                row = [str(record.get(header, '')) for header in headers]
                table_data.append(row)
            
            # Create table
            table = Table(table_data)
            
            # Style table
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
        else:
            no_data_para = Paragraph("No attendance data found.", styles['Normal'])
            elements.append(no_data_para)
        
        # Build PDF
        doc.build(elements)
        
        return output_path
        
    except Exception as e:
        print(f"Error exporting to PDF: {e}")
        return None

def generate_student_report(student, attendance_records, start_date=None, end_date=None):
    """
    Generate individual student attendance report
    Args:
        student: Student object
        attendance_records: List of attendance records
        start_date: Start date for report
        end_date: End date for report
    Returns:
        dict: Report data
    """
    try:
        # Filter records by date range if provided
        if start_date:
            attendance_records = [r for r in attendance_records if r.scan_time.date() >= start_date]
        if end_date:
            attendance_records = [r for r in attendance_records if r.scan_time.date() <= end_date]
        
        # Calculate statistics
        total_days = len(set(r.scan_time.date() for r in attendance_records))
        total_scans = len(attendance_records)
        late_arrivals = len([r for r in attendance_records if r.is_late])
        rooms_visited = len(set(r.room_id for r in attendance_records))
        
        # Group by date
        daily_attendance = {}
        for record in attendance_records:
            date_key = record.scan_time.date()
            if date_key not in daily_attendance:
                daily_attendance[date_key] = []
            daily_attendance[date_key].append(record)
        
        report_data = {
            'student_info': {
                'name': student.get_full_name(),
                'student_no': student.student_no,
                'department': student.department,
                'section': student.section,
                'year_level': student.year_level
            },
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            },
            'summary': {
                'total_days_attended': total_days,
                'total_scans': total_scans,
                'late_arrivals': late_arrivals,
                'on_time_percentage': round(((total_scans - late_arrivals) / total_scans * 100), 2) if total_scans > 0 else 0,
                'rooms_visited': rooms_visited
            },
            'daily_breakdown': {
                str(date): {
                    'scans': len(records),
                    'rooms': [r.room.get_full_name() for r in records],
                    'times': [r.scan_time.strftime('%H:%M:%S') for r in records],
                    'late_count': len([r for r in records if r.is_late])
                }
                for date, records in daily_attendance.items()
            },
            'records': [
                {
                    'date': r.scan_time.date().isoformat(),
                    'time': r.scan_time.time().isoformat(),
                    'room': r.room.get_full_name() if r.room else 'Unknown',
                    'is_late': r.is_late,
                    'scanner': r.scanned_by_user.username if r.scanned_by_user else 'System'
                }
                for r in sorted(attendance_records, key=lambda x: x.scan_time, reverse=True)
            ]
        }
        
        return report_data
        
    except Exception as e:
        print(f"Error generating student report: {e}")
        return None

def generate_room_report(room, attendance_records, start_date=None, end_date=None):
    """
    Generate room attendance report
    Args:
        room: Room object
        attendance_records: List of attendance records
        start_date: Start date for report
        end_date: End date for report
    Returns:
        dict: Report data
    """
    try:
        # Filter records by date range if provided
        if start_date:
            attendance_records = [r for r in attendance_records if r.scan_time.date() >= start_date]
        if end_date:
            attendance_records = [r for r in attendance_records if r.scan_time.date() <= end_date]
        
        # Calculate statistics
        total_scans = len(attendance_records)
        unique_students = len(set(r.student_id for r in attendance_records))
        unique_days = len(set(r.scan_time.date() for r in attendance_records))
        late_arrivals = len([r for r in attendance_records if r.is_late])
        
        # Group by date
        daily_stats = {}
        for record in attendance_records:
            date_key = record.scan_time.date()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'students': set(),
                    'total_scans': 0,
                    'late_count': 0
                }
            
            daily_stats[date_key]['students'].add(record.student_id)
            daily_stats[date_key]['total_scans'] += 1
            if record.is_late:
                daily_stats[date_key]['late_count'] += 1
        
        # Convert sets to counts
        for date, stats in daily_stats.items():
            stats['unique_students'] = len(stats['students'])
            del stats['students']
        
        report_data = {
            'room_info': {
                'name': room.get_full_name(),
                'room_number': room.room_number,
                'building': room.building,
                'capacity': room.capacity,
                'room_type': room.room_type
            },
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            },
            'summary': {
                'total_scans': total_scans,
                'unique_students': unique_students,
                'unique_days': unique_days,
                'late_arrivals': late_arrivals,
                'average_daily_attendance': round(unique_students / unique_days, 2) if unique_days > 0 else 0,
                'capacity_utilization': round((unique_students / room.capacity * 100), 2) if room.capacity > 0 else 0
            },
            'daily_breakdown': {
                str(date): stats for date, stats in daily_stats.items()
            },
            'records': [
                {
                    'date': r.scan_time.date().isoformat(),
                    'time': r.scan_time.time().isoformat(),
                    'student': r.student.get_full_name() if r.student else 'Unknown',
                    'student_no': r.student.student_no if r.student else 'N/A',
                    'is_late': r.is_late,
                    'scanner': r.scanned_by_user.username if r.scanned_by_user else 'System'
                }
                for r in sorted(attendance_records, key=lambda x: x.scan_time, reverse=True)
            ]
        }
        
        return report_data
        
    except Exception as e:
        print(f"Error generating room report: {e}")
        return None

def export_students_to_excel(students_data, filename=None):
    """
    Export students data to Excel file
    Args:
        students_data (list): List of student dictionaries
        filename (str): Output filename
    Returns:
        str: Path to created file
    """
    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"students_list_{timestamp}.xlsx"
        
        output_path = os.path.join('exports', filename)
        os.makedirs('exports', exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(students_data)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Students']
            
            # Format header
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min((max_length + 2) * 1.2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output_path
        
    except Exception as e:
        print(f"Error exporting students to Excel: {e}")
        return None

def get_export_summary(export_path, record_count):
    """
    Get export summary information
    Args:
        export_path (str): Path to exported file
        record_count (int): Number of records exported
    Returns:
        dict: Export summary
    """
    try:
        file_stats = os.stat(export_path)
        
        return {
            'file_path': export_path,
            'file_name': os.path.basename(export_path),
            'file_size': file_stats.st_size,
            'file_size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'record_count': record_count,
            'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            'success': True
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }