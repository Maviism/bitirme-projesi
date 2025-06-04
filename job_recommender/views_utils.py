from .models import Student

def get_current_student(request):
    """
    Get the student profile for the currently logged-in user.
    Similar to the function in resume_generator/views.py but simplified for job_recommender.
    
    Returns:
        Student object or None if not found
    """
    if request.user.is_authenticated:
        try:
            # First try to find student profiles directly linked to the user
            student_profiles = Student.objects.filter(user=request.user)
            if student_profiles.exists():
                # Get the most recently updated student profile
                return student_profiles.order_by('-updated_at').first()
            
            # Try to find student by student_id matching username
            try:
                student = Student.objects.get(student_id=request.user.username)
                
                # Link this student to the user if not already linked
                if not student.user:
                    student.user = request.user
                    student.save(update_fields=['user'])
                
                return student
            except Student.DoesNotExist:
                pass
            
            # Try by email if available
            if hasattr(request.user, 'email') and request.user.email:
                try:
                    # Look for students with email field
                    student = Student.objects.filter(email=request.user.email).first()
                    if student:
                        # Link this student to the user if not already linked
                        if not student.user:
                            student.user = request.user
                            student.save(update_fields=['user'])
                        
                        return student
                except Exception:
                    pass
        except Exception:
            pass
    
    return None
