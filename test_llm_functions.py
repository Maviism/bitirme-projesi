#!/usr/bin/env python
"""
Quick test script untuk LLM functions
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/maviism/bitirme-projesi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from utils.llm_utils import get_llm_instance

def test_resume_generation():
    print("🧪 Testing Resume Generation...")
    
    # Sample user data
    user_data = {
        'personal_info': {
            'name': 'John Doe',
            'faculty': 'Engineering',
            'program': 'Computer Science',
            'gpa': '3.8'
        },
        'skills': ['Python', 'Django', 'JavaScript', 'React'],
        'courses': [
            {'name': 'Web Development', 'grade': 'A'},
            {'name': 'Database Systems', 'grade': 'A-'}
        ],
        'internships': [
            {
                'company': 'Tech Corp',
                'position': 'Software Engineering Intern',
                'duration': '3 months',
                'description': 'Developed web applications using Django'
            }
        ]
    }
    
    job_description = "We are looking for a Python developer with Django experience for web development."
    
    try:
        llm = get_llm_instance()
        result = llm.generate_resume_content(user_data, job_description)
        
        print("✅ Resume generation successful!")
        print(f"Professional Summary: {result.get('professional_summary', 'N/A')}")
        print(f"Skills: {result.get('skills', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Resume generation failed: {e}")
        return False

def test_job_compatibility():
    print("\n🧪 Testing Job Compatibility Analysis...")
    
    user_profile = {
        'skills': ['Python', 'Django', 'JavaScript'],
        'experience_level': 'Junior',
        'education': 'Computer Science',
        'gpa': 3.8
    }
    
    job_data = {
        'title': 'Junior Python Developer',
        'company': 'StartupXYZ',
        'required_skills': ['Python', 'Django', 'REST APIs'],
        'experience_required': '0-2 years',
        'description': 'Building web applications with Python and Django...'
    }
    
    try:
        llm = get_llm_instance()
        result = llm.analyze_job_compatibility(user_profile, job_data)
        
        print("✅ Job compatibility analysis successful!")
        print(f"Compatibility Score: {result.get('compatibility_score', 'N/A')}%")
        print(f"Matching Skills: {result.get('matching_skills', 'N/A')}")
        print(f"Missing Skills: {result.get('missing_skills', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Job compatibility analysis failed: {e}")
        return False

def test_text_improvement():
    print("\n🧪 Testing Text Improvement...")
    
    original_text = "I am a computer science student looking for opportunities."
    
    try:
        llm = get_llm_instance()
        improved = llm.improve_resume_section(
            section_content=original_text,
            section_type="professional_summary",
            job_context="Software Developer position"
        )
        
        print("✅ Text improvement successful!")
        print(f"Original: {original_text}")
        print(f"Improved: {improved}")
        return True
    except Exception as e:
        print(f"❌ Text improvement failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting LLM Utils Tests...")
    
    tests = [
        test_resume_generation,
        test_job_compatibility,
        test_text_improvement
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! LLM Utils is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
