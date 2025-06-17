"""
User and Student utility functions for the application
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_student(request):
    """
    Get the student profile for the currently logged-in user.
    This is a centralized utility function used by multiple apps.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Student object or None if not found
    """
    if request.user.is_authenticated:
        try:
            # Import here to avoid circular imports
            from job_recommender.models import Student
            
            # Get the username
            username = request.user.username
            logger.info(f"Finding student for authenticated user: {username}")
            
            # Check if a specific student ID is requested from the session or URL parameter
            requested_student_id = request.session.get('active_student_id') or request.GET.get('student_profile_id')
            if requested_student_id:
                try:
                    # Try to get the specific student
                    student = Student.objects.get(id=requested_student_id, user=request.user)
                    logger.info(f"Using specifically requested student: {student.fullname} {student.last_name}")
                    return student
                except Student.DoesNotExist:
                    logger.warning(f"Requested student ID {requested_student_id} not found or doesn't belong to user")
            
            # First try to find student profiles directly linked to the user
            student_profiles = Student.objects.filter(user=request.user)
            if student_profiles.exists():
                # Get the most recently updated student profile
                student = student_profiles.order_by('-updated_at').first()
                logger.info(f"Found student by user relation: {student.fullname} {student.last_name}")
                return student
            
            # Try to find student by student_id matching username
            try:
                student = Student.objects.get(student_id=username)
                logger.info(f"Found student by matching student_id: {student.fullname} {student.last_name}")
                
                # Link this student to the user if not already linked
                if not student.user:
                    student.user = request.user
                    student.save(update_fields=['user'])
                    logger.info(f"Linked student {student.student_id} to user {username}")
                
                return student
            except Student.DoesNotExist:
                logger.info(f"No student found with student_id={username}")
            
            # Try by email if available
            if hasattr(request.user, 'email') and request.user.email:
                try:
                    # Look for students with email field
                    student = Student.objects.filter(email=request.user.email).first()
                    if student:
                        logger.info(f"Found student by email: {student.fullname} {student.last_name}")
                        
                        # Link this student to the user if not already linked
                        if not student.user:
                            student.user = request.user
                            student.save(update_fields=['user'])
                            logger.info(f"Linked student with email {request.user.email} to user {username}")
                        
                        return student
                except Exception as e:
                    logger.info(f"Could not find student by email: {e}")
            
            # Log warning if no student is found
            logger.warning(f"No student record found for user: {username}")
            
        except Exception as e:
            logger.error(f"Error finding student for user: {e}")
    else:
        logger.warning("User is not authenticated")
    
    return None
