"""
Resume Generator utilities for generating resume content using LLM.
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import date
from django.shortcuts import get_object_or_404

from utils.llm_utils import LLMProvider, LLMUtils

# Configure logging
logger = logging.getLogger(__name__)


def generate_resume_content(llm_utils: LLMUtils, user_data: Dict, job_description: str = "") -> Dict:
    """
    Generate resume content based on user data and optional job description
    
    Args:
        llm_utils: The LLM utility instance to use for text generation
        user_data: Dictionary containing user information
        job_description: Optional job description for tailoring
        
    Returns:
        Dictionary with generated resume sections
    """
    prompt = f"""
    Aşağıdaki kullanıcı verilerine dayanarak profesyonel bir özgeçmiş içeriği oluşturun. Türkçe doğal dil kullanın ve iş dünyasında kabul görmüş terimler kullanın.

    Kullanıcı Bilgileri:
    {json.dumps(user_data, indent=2)}

    {f"Hedeflenen İş Pozisyonu ve Açıklama: {job_description}" if job_description else ""}

    Aşağıdaki bölümleri içeren kapsamlı bir özgeçmiş oluşturun:

    1. Profesyonel Özet (2-3 cümle): 
       - Kişinin güçlü yönlerini vurgulayan
       - Kariyer hedeflerini belirten  
       - İş pozisyonuna uygun yetenekleri öne çıkaran

    2. Yetenekler:
       - Teknik beceriler
       - Yazılım ve araçlar
       - Kişisel özellikler
       - Dil becerileri (varsa)

    3. Deneyim:
       - Kurum adı ve pozisyon
       - Görev süreleri
       - Başarılar ve sorumluluklar (sayısal verilerle desteklenen)
       - Kullanılan teknolojiler

    4. Eğitim:
       - Üniversite ve fakülte
       - Bölüm ve GNO
       - Mezuniyet tarihi
       - Akademik başarılar

    5. Projeler (varsa):
       - Proje adı ve açıklaması
       - Kullanılan teknolojiler
       - Elde edilen sonuçlar

    6. Sertifikalar ve Kurslar (varsa):
       - Alınan sertifikalar
       - Tamamlanan kurslar
       - Eğitim platformları

    İçerik şu kriterleri karşılamalı:
    - Türkçe iş dünyası terminolojisini kullanın
    - ATS (Applicant Tracking System) dostu olsun
    - Özgün ve kişiselleştirilmiş olsun
    - Ölçülebilir başarılar içersin
    - Profesyonel ve etkili bir dil kullanın
    - İş pozisyonuna özel anahtar kelimeler içersin
    """
    
    schema = {
        "professional_summary": "string",
        "skills": {
            "technical_skills": ["string"],
            "soft_skills": ["string"],
            "languages": ["string"],
            "tools_and_software": ["string"]
        },            "experience": [
                {
                    "institution": "string",
                    "position": "string",
                    "duration": "string",
                    "location": "string",
                    "description": "string",
                    "achievements": ["string"],
                    "technologies_used": ["string"]
                }
            ],
        "education": [
            {
                "institution": "string",
                "degree": "string",
                "field_of_study": "string",
                "graduation_year": "string",
                "gpa": "string",
                "honors": ["string"],
                "relevant_coursework": ["string"]
            }
        ],
        "projects": [
            {
                "name": "string",
                "description": "string",
                "technologies": ["string"],
                "link": "string",
                "achievements": ["string"]
            }
        ],
        "certifications": [
            {
                "name": "string",
                "issuer": "string",
                "date": "string",
                "credential_id": "string"
            }
        ],
        "volunteer_work": [
            {
                "organization": "string",
                "role": "string",
                "duration": "string",
                "description": "string"
            }
        ]
    }
    
    return llm_utils.provider.generate_json(prompt, schema)

def improve_resume_section(llm_utils: LLMUtils, section_content: str, section_type: str, job_context: str = "") -> str:
    """
    Improve a specific resume section
    
    Args:
        llm_utils: The LLM utility instance to use for text generation
        section_content: Current content of the section
        section_type: Type of section (summary, experience, skills, etc.)
        job_context: Optional job context for tailoring
        
    Returns:
        Improved section content
    """
    prompt = f"""
    Aşağıdaki özgeçmiş bölümünü geliştirin ve daha etkili hale getirin:

    Bölüm Türü: {section_type}
    Mevcut İçerik:
    {section_content}

    {f"İş Pozisyonu Bağlamı: {job_context}" if job_context else ""}

    Bölümü şu açılardan geliştirin:

    1. Profesyonellik: İş dünyasına uygun Türkçe terminoloji kullanın
    2. Etki: Güçlü eylem fiilleri ve ölçülebilir başarılar ekleyin  
    3. ATS Uyumluluğu: Anahtar kelimeler ve sektör terimleri kullanın
    4. Özgünlük: Standart ifadelerden kaçının, kişiselleştirilmiş içerik oluşturun
    5. Okuma Kolaylığı: Net ve anlaşılır ifadeler kullanın

    Bölüm türüne özel geliştirmeler:
    - Özet: Kişinin güçlü yönlerini, kariyer hedeflerini ve değer önerisini vurgulayın
    - Deneyim: Başarıları sayısal verilerle destekleyin, sorumlulukları net açıklayın
    - Beceriler: Teknik ve kişisel becerileri kategorize edin, yeterlilik seviyelerini belirtin
    - Eğitim: Akademik başarıları, önemli projeleri ve dersleri vurgulayın
    - Projeler: Projenin etkisini, kullanılan teknolojileri ve sonuçları detaylı açıklayın

    Sadece geliştirilen içeriği döndürün, ek açıklama yapmayın.
    """
    
    return llm_utils.provider.generate_text(prompt)

def generate_cover_letter_content(llm_utils: LLMUtils, user_data: Dict, job_data: Dict) -> str:
    """
    Generate a personalized cover letter
    
    Args:
        llm_utils: The LLM utility instance to use for text generation
        user_data: User's background and experience
        job_data: Job description and position information
        
    Returns:
        Generated cover letter text
    """
    prompt = f"""
    Aşağıdaki bilgilere dayanarak profesyonel ve kişiselleştirilmiş bir İnsan Kaynakları ön yazısı (cover letter) oluşturun:

    Başvuran Bilgileri:
    {json.dumps(user_data, indent=2)}

    İş Pozisyonu Bilgileri:
    {json.dumps(job_data, indent=2)}

    Ön yazı şu özellikleri taşımalı:

    1. Profesyonel Format:
       - Tarih ve adres bilgileri
       - Uygun hitap şekli
       - Profesyonel kapanış

    2. İçerik Yapısı:
       - Giriş Paragrafı: Hangi pozisyona başvurduğunu belirt, ilgi çekici bir açılış yap
       - Gelişme Paragrafları: 
         * İlgili deneyim ve becerilerini vurgula
         * Pozisyona uygunluğunu göster
         * Somut başarılar ve örnekler ver
         * İlgili alana olan ilgini ve bilgini göster
       - Sonuç Paragrafı: Görüşme talebi ve teşekkür

    3. Dil ve Üslup:
       - Türkçe iş dünyası terminolojisi kullan
       - Özgüvenli ama mütevazı bir ton
       - Kişiselleştirilmiş ve özgün ifadeler
       - Standart kalıplardan kaçın

    4. Özelleştirme:
       - Pozisyonun gereksinimlerine odaklanma
       - Başvuranın güçlü yönlerini öne çıkarma
       - Sunabileceği katma değeri vurgulama

    Yaklaşık 3-4 paragraf uzunluğunda, samimi ama profesyonel bir ön yazı oluşturun.
    """
    
    return llm_utils.provider.generate_text(prompt)

def improve_cover_letter(llm_utils: LLMUtils, improvement_context: Dict) -> str:
    """
    Improve an existing cover letter
    
    Args:
        llm_utils: The LLM utility instance to use for text generation
        improvement_context: Context for improving the cover letter, including:
                             - current_letter: The existing cover letter text
                             - job_info: Job title and description
                             - candidate_info: Candidate's background
                             - improvement_goals: Specific aims for improvement
                             
    Returns:
        Improved cover letter text
    """
    prompt = f"""
    Aşağıda verilen mevcut ön yazıyı (cover letter) iyileştirin ve geliştirin:

    MEVCUT ÖN YAZI:
    {improvement_context.get('current_letter', '')}

    İŞ BİLGİSİ:
    {json.dumps(improvement_context.get('job_info', {}), indent=2)}

    ADAY BİLGİSİ:
    {json.dumps(improvement_context.get('candidate_info', {}), indent=2)}

    İYİLEŞTİRME HEDEFLERİ:
    {json.dumps(improvement_context.get('improvement_goals', []), indent=2)}

    Bu iyileştirmeleri yaparken şunlara dikkat edin:
    1. Mevcut ön yazının genel yapısını koruyun, ancak dili daha ikna edici ve etkileyici hale getirin
    2. Aday ve iş arasındaki uyumu daha güçlü vurgulayın
    3. Daha kişisel ve özgün ifadeler kullanın
    4. Somut beceriler ve deneyimleri daha iyi öne çıkarın
    5. Adayın benzersiz değer önerisini güçlendirin
    6. Profesyonel ama samimi bir ton yakalayın

    Sadece iyileştirilmiş ön yazının tam metnini üretin, ek açıklama yapmayın veya başka metin eklemeyin.
    """
    
    return llm_utils.provider.generate_text(prompt)

# New utility functions for handling common operations

def calculate_duration_months(start_date, end_date):
    """Calculate duration between two dates in months"""
    if not start_date:
        return 0
    
    end = end_date or date.today()
    
    months = (end.year - start_date.year) * 12 + (end.month - start_date.month)
    return max(months, 1)  # Minimum 1 month

def get_student_data_for_resume(student_obj, request_data=None):
    """
    Get formatted student data for resume generation
    
    Args:
        student_obj: Student model instance
        request_data: Optional POST data from request to override student data
        
    Returns:
        Dictionary with student data formatted for resume
    """
    from job_recommender.models import Student, Course, Experience
    
    # Get skills from request data or student object
    skills_str = request_data.get('student_skills', '') if request_data else ''
    
    # Create the student data dictionary
    student_data = {
        'fullname': request_data.get('student_fullname', student_obj.fullname) if request_data else student_obj.fullname,
        'last_name': request_data.get('student_last_name', student_obj.last_name) if request_data else student_obj.last_name,
        'email': request_data.get('student_email', getattr(student_obj, 'email', '')) if request_data else getattr(student_obj, 'email', ''),
        'phone': request_data.get('student_phone', getattr(student_obj, 'phone', '')) if request_data else getattr(student_obj, 'phone', ''),
        'linkedin_profile': request_data.get('student_linkedin', getattr(student_obj, 'linkedin_profile', '')) if request_data else getattr(student_obj, 'linkedin_profile', ''),
        'faculty': student_obj.faculty,
        'program': student_obj.program,
        'gpa': str(student_obj.gpa),
        'skills': [s.strip() for s in skills_str.split(',') if s.strip()] if skills_str else student_obj.skills,
        'summary': request_data.get('student_summary', getattr(student_obj, 'summary', '')) if request_data else getattr(student_obj, 'summary', ''),
        'courses': Course.objects.filter(student=student_obj),
        'internships': Experience.objects.filter(student=student_obj, experience_type='internship'),
        'organizations': Experience.objects.filter(student=student_obj, experience_type='organization'),
    }
    
    return student_data

def get_template_name(template_style):
    """Get resume template name based on style"""
    if template_style == 'modern':
        return 'resume_generator/resume_template_modern.html'
    else:  # Default to ATS
        return 'resume_generator/resume_template_ats.html'

def get_context_for_resume_template(job_title, job_company, job_description, student_data, is_preview=False):
    """
    Create context dictionary for resume template
    
    Args:
        job_title: Job title
        job_company: Company name
        job_description: Job description
        student_data: Student data dictionary
        is_preview: Whether this is a preview (default: False)
        
    Returns:
        Context dictionary for template rendering
    """
    return {
        'job_title': job_title,
        'job_company': job_company,
        'job_description': job_description,
        'student': student_data,
        'is_preview': is_preview
    }

def get_enhanced_user_data_for_llm(student_obj, job_recommendations=None):
    """
    Prepare enhanced user data for LLM
    
    Args:
        student_obj: Student model instance
        job_recommendations: List of job recommendations (optional)
        
    Returns:
        Dictionary with comprehensive user data for LLM
    """
    from job_recommender.models import Student, Course, Experience
    
    # Create a comprehensive user data dictionary for the LLM
    user_data = {
        'personal_info': {
            'name': f"{student_obj.fullname} {student_obj.last_name}",
            'email': getattr(student_obj, 'email', ''),
            'phone': getattr(student_obj, 'phone', ''),
            'linkedin': getattr(student_obj, 'linkedin_profile', ''),
            'student_id': student_obj.student_id,
            'birth_date': student_obj.birth_date.strftime('%Y-%m-%d') if student_obj.birth_date else '',
            'is_alumni': student_obj.is_alumni,
            'faculty': student_obj.faculty,
            'program': student_obj.program,
            'gpa': str(student_obj.gpa)
        },
        'skills': student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else [],
        'courses': [
            {
                'code': course.code,
                'name': course.name,
                'grade': getattr(course, 'grade', 'N/A'),
                'success_level': 'yüksek' if course.grade in ['AA', 'BA'] else 'orta' if course.grade in ['BB', 'CB'] else 'düşük' if course.grade not in ['--', 'N/A'] else 'belirsiz'
            } for course in Course.objects.filter(student=student_obj).order_by('-grade')
        ],
        'experience': {
            'internships': [
                {
                    'institution': internship.institution_name,
                    'position': getattr(internship, 'position', 'Stajyer'),
                    'start_date': internship.start_date.strftime('%Y-%m-%d') if internship.start_date else '',
                    'end_date': internship.end_date.strftime('%Y-%m-%d') if internship.end_date else 'Devam ediyor',
                    'duration': f"{internship.start_date} - {internship.end_date or 'Devam ediyor'}",
                    'description': getattr(internship, 'description', ''),
                    'is_current': not internship.end_date
                } for internship in Experience.objects.filter(student=student_obj, experience_type='internship').order_by('-start_date')
            ],
            'organizations': [
                {
                    'name': org.institution_name,
                    'role': getattr(org, 'position', 'Üye'),
                    'start_date': org.start_date.strftime('%Y-%m-%d') if org.start_date else '',
                    'end_date': org.end_date.strftime('%Y-%m-%d') if org.end_date else 'Devam ediyor',
                    'duration': f"{org.start_date} - {org.end_date or 'Devam ediyor'}",
                    'description': getattr(org, 'description', ''),
                    'is_current': not org.end_date
                } for org in Experience.objects.filter(student=student_obj, experience_type='organization').order_by('-start_date')
            ]
        },
        'academic_performance': {
            'total_courses': Course.objects.filter(student=student_obj).count(),
            'high_grades_count': Course.objects.filter(student=student_obj, grade__in=['AA', 'BA']).count(),
            'gpa_level': 'yüksek' if float(student_obj.gpa) >= 3.0 else 'orta' if float(student_obj.gpa) >= 2.5 else 'düşük',
            'graduation_status': 'mezun' if student_obj.is_alumni else 'öğrenci'
        },
        'career_context': {
            'has_internship_experience': Experience.objects.filter(student=student_obj, experience_type='internship').exists(),
            'has_organization_experience': Experience.objects.filter(student=student_obj, experience_type='organization').exists(),
            'total_experiences': Experience.objects.filter(student=student_obj).count(),
            'has_leadership_experience': any(['başkan' in exp.position.lower() or 'lider' in exp.position.lower() 
                                              for exp in Experience.objects.filter(student=student_obj) 
                                              if hasattr(exp, 'position') and exp.position])
        }
    }
    
    # Add job recommendations if provided
    if job_recommendations:
        user_data['job_recommendations'] = job_recommendations
        
    return user_data

def get_comprehensive_job_data(job_title, job_description):
    """
    Create a comprehensive job data dictionary for LLM
    
    Args:
        job_title: Job title
        job_description: Job description
        
    Returns:
        Dictionary with job data formatted for LLM
    """
    return {
        'position': {
            'title': job_title,
            'description': job_description
        },
        'job_context': {
            'field': 'teknoloji',  # Could be enhanced with job field data
            'skills_required': ['inovasyon', 'ekip çalışması', 'sürekli gelişim']  # Could be enhanced
        },
        'application_context': {
            'application_date': date.today().strftime('%Y-%m-%d'),
            'source': 'kariyer portalı',
            'motivation': 'kariyer gelişimi ve deneyim kazanımı'
        }
    }

def get_error_response(error_message, status_code=500):
    """
    Create an error response with HTML content
    
    Args:
        error_message: Error message to display
        status_code: HTTP status code (default: 500)
        
    Returns:
        HttpResponse with error message and status code
    """
    from django.http import HttpResponse
    
    error_html = f"""
    <html>
    <head>
        <title>Error</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
            .error-container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #f44336; border-radius: 5px; }}
            .error-title {{ color: #f44336; }}
            .error-details {{ background-color: #f9f9f9; padding: 10px; border-left: 3px solid #f44336; }}
            .back-button {{ display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #4CAF50; color: white; 
                           text-decoration: none; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <h2 class="error-title">Error</h2>
            <p>{error_message}</p>
            <a href="javascript:history.back()" class="back-button">Go Back</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(error_html, status=status_code)

def generate_fallback_cover_letter(student_obj, job_title="pozisyon"):
    """
    Generate a fallback cover letter when LLM is not available
    
    Args:
        student_obj: Student model instance
        job_title: Job title for the application
        
    Returns:
        str: Fallback cover letter content
    """
    # Create skills list in Turkish
    skills_list = student_obj.skills if isinstance(student_obj.skills, list) else [student_obj.skills] if student_obj.skills else ['problem çözme', 'iletişim', 'ekip çalışması']
    skills_text = ', '.join(skills_list[:3]) if len(skills_list) >= 3 else ', '.join(skills_list + ['analitik düşünce', 'hızlı öğrenme'][:3-len(skills_list)])
    
    return f"""Sayın İnsan Kaynakları Müdürü,

{job_title} pozisyonuna olan ilgimi ve başvurumu bildirmek isterim. {student_obj.faculty} {student_obj.program} bölümünden {student_obj.gpa} GNO ile {"mezun" if student_obj.is_alumni else "son sınıf öğrencisi"} olarak, edindiğim bilgi ve becerileri takımınıza katkı sağlamak için sabırsızlanıyorum.

Akademik geçmişim ve sahip olduğum {skills_text} gibi yetenekler sayesinde bu pozisyonda başarılı olabileceğime inanıyorum. {"Mezuniyet" if student_obj.is_alumni else "Öğrencilik"} sürecimde edindiğim teorik bilgileri pratik deneyimlerle harmanlayarak, hem bireysel hem de ekip halinde çalışabilen bir profil geliştirdim.

Bu alandaki güncel gelişmeleri ve profesyonel standartları yakından takip ediyorum. Niteliklerimin pozisyonun gereklilikleriyle ne kadar uyumlu olduğunu görüşme sürecinde detaylı olarak paylaşma fırsatı bulabilirsem çok memnun olurum.

Zamanınız ve ilginiz için teşekkür ederim.

Saygılarımla,
{student_obj.fullname} {student_obj.last_name}"""

def generate_fallback_resume_content(student_obj):
    """
    Generate fallback resume content when LLM is not available
    
    Args:
        student_obj: Student model instance
        
    Returns:
        dict: Fallback resume content
    """
    return {
        'summary': f"Recent graduate from {student_obj.program} at {student_obj.faculty} with a GPA of {student_obj.gpa}. Seeking opportunities to apply academic knowledge in a professional setting.",
        'skills': ["Communication", "Time Management", "Problem Solving", "Critical Thinking"] + (student_obj.skills if isinstance(student_obj.skills, list) else [])
    }
