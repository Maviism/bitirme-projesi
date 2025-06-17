"""
Resume Generator utilities for generating resume content using LLM.
"""

import json
import logging
from typing import Dict

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
