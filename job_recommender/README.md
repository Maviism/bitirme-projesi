# Job Recommender App

Aplikasi sistem rekomendasi pekerjaan berbasis AI dan machine learning yang menggunakan pendekatan hybrid untuk memberikan rekomendasi pekerjaan yang personal untuk mahasiswa dan alumni.

## Daftar Isi
- [Ikhtisar](#ikhtisar)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Sistem Rekomendasi](#sistem-rekomendasi)
- [Alur Kerja](#alur-kerja)
- [Model Database](#model-database)
- [API Endpoints](#api-endpoints)
- [Teknologi yang Digunakan](#teknologi-yang-digunakan)
- [Instalasi dan Setup](#instalasi-dan-setup)

## Ikhtisar

Job Recommender adalah aplikasi Django yang menyediakan sistem rekomendasi pekerjaan cerdas untuk mahasiswa dan alumni. Aplikasi ini menggunakan pendekatan hybrid yang menggabungkan:

1. **Alumni-based Recommendation**: Rekomendasi berdasarkan profil akademik alumni yang sukses
2. **Experience-based Recommendation**: Rekomendasi berdasarkan pengalaman organisasi dan magang
3. **AI-powered Analysis**: Analisis kompatibilitas menggunakan Large Language Model (LLM)

## Arsitektur Sistem

```
job_recommender/
├── models.py          # Model database (Student, Job, Alumni, dll.)
├── recommender.py     # Engine sistem rekomendasi hybrid
├── views.py           # View handlers untuk web dan API
├── views.py           # Views for the job recommender app (uses utils.user_utils)
├── urls.py            # URL routing
├── admin.py           # Django admin configuration
└── templates/         # Template HTML untuk UI
```

## Sistem Rekomendasi

### 1. Hybrid Recommender Engine

Sistem rekomendasi utama menggunakan class `HybridRecommender` yang menggabungkan dua pendekatan:

#### A. Alumni-based Recommendations
- **Input**: Profil akademik mahasiswa (GPA, mata kuliah, program studi)
- **Proses**: 
  - Mencari alumni dengan profil akademik serupa
  - Menghitung similarity score berdasarkan:
    - Program studi (bonus 1.5x jika sama)
    - GPA similarity (1 - |difference|/4.0)
    - Course similarity berdasarkan mata kuliah yang diambil
    - Skills matching bonus
- **Output**: Jobs dari alumni dengan profil serupa

#### B. Experience-based Recommendations
- **Input**: Pengalaman organisasi dan magang mahasiswa
- **Proses**:
  - Menggunakan **Sentence-BERT** (all-MiniLM-L6-v2) untuk encoding pengalaman
  - Menghitung cosine similarity antara pengalaman mahasiswa dengan deskripsi pekerjaan
  - Memberikan bonus untuk program studi yang cocok
  - Memberikan bonus untuk skills yang sesuai
- **Output**: Jobs dengan similarity score tertinggi

#### C. Hybrid Scoring
```python
final_score = (alumni_score * 0.6) + (experience_score * 0.4)
```

### 2. AI-Powered Features

#### A. Job Compatibility Analysis
- Menggunakan LLM untuk analisis mendalam kompatibilitas
- Input: Profil lengkap mahasiswa + detail pekerjaan
- Output: Analisis terstruktur tentang kesesuaian kandidat

#### B. Career Advice
- Memberikan saran karir personal menggunakan AI
- Rekomendasi skill development dan career path

#### C. Skill Gap Analysis
- Menganalisis kesenjangan skill untuk posisi target
- Memberikan roadmap pembelajaran dan pengembangan skill

## Alur Kerja

### 1. Data Input Flow
```
User Input → Career Form → Data Validation → Database Storage
```

1. **Career Form**: Mahasiswa mengisi form dengan data:
   - Informasi personal (nama, fakultas, program, GPA)
   - Mata kuliah dan nilai
   - Pengalaman organisasi dan magang
   - Skills dan preferensi

2. **Data Processing**: System memproses dan validasi data
3. **Database Storage**: Data disimpan ke models terkait

### 2. Recommendation Generation Flow
```
Student Profile → Hybrid Recommender → Recommendation Scoring → Results Display
```

1. **Profile Retrieval**: Sistem mengambil profil mahasiswa
2. **Alumni Matching**: Mencari alumni dengan profil serupa
3. **Experience Analysis**: Analisis pengalaman menggunakan NLP
4. **Hybrid Scoring**: Kombinasi weighted scoring
5. **Ranking**: Sort berdasarkan match score
6. **Storage**: Simpan rekomendasi ke `JobRecommendation` model

### 3. AI Analysis Flow
```
User Request → LLM Processing → Structured Response → User Interface
```

## Model Database

### Student Model
```python
class Student(models.Model):
    user = models.ForeignKey(User, ...)
    student_id = models.CharField(max_length=20, unique=True)
    fullname = models.CharField(max_length=100)
    program = models.CharField(max_length=100)
    gpa = models.DecimalField(max_digits=3, decimal_places=2)
    skills = models.JSONField(default=list)  # Skills array
    is_alumni = models.BooleanField(default=False)
```

### Alumni Model
```python
class Alumni(models.Model):
    student = models.OneToOneField(Student, ...)
    graduation_date = models.DateField()
    current_job = models.ForeignKey('Job', ...)
    current_company = models.CharField(max_length=100)
```

### Job Model
```python
class Job(models.Model):
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    description = models.TextField()
    required_majors = models.JSONField(default=list)
    required_skills = models.JSONField(default=list)
```

### JobRecommendation Model
```python
class JobRecommendation(models.Model):
    student = models.ForeignKey(Student, ...)
    job = models.ForeignKey(Job, ...)
    match_score = models.DecimalField(max_digits=5, decimal_places=2)
    source = models.CharField(max_length=20)  # 'alumni', 'job_posting', 'hybrid'
```

### Experience Model
```python
class Experience(models.Model):
    student = models.ForeignKey(Student, ...)
    experience_type = models.CharField(max_length=20)  # 'organization' or 'internship'
    institution_name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    description = models.TextField()
```

## API Endpoints

### Core Endpoints
- `GET /` - Landing page
- `GET /career-form/` - Form input untuk profil mahasiswa
- `POST /api/submit-application/` - Submit profil dan dapat rekomendasi
- `GET /recommendation-results/` - Tampilkan hasil rekomendasi

### AI-Powered Endpoints
- `POST /api/analyze-compatibility/` - Analisis kompatibilitas job
- `POST /api/ai-recommendations/` - Rekomendasi berbasis AI
- `POST /api/career-advice/` - Saran karir personal
- `POST /api/skill-gap-analysis/` - Analisis kesenjangan skill

## Teknologi yang Digunakan

### Backend
- **Django**: Web framework
- **PostgreSQL/SQLite**: Database
- **Sentence Transformers**: NLP untuk similarity matching
- **LLM Integration**: AI analysis (melalui utils.llm_utils)

### Machine Learning
- **Sentence-BERT**: Text embedding untuk experience matching
- **Cosine Similarity**: Perhitungan similarity score
- **Weighted Hybrid Approach**: Kombinasi multiple recommendation sources

### Frontend
- **HTML/CSS/JavaScript**: Web interface
- **AJAX**: Asynchronous form submission
- **Bootstrap**: UI styling

## Instalasi dan Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Migration
```bash
python manage.py makemigrations job_recommender
python manage.py migrate
```

### 3. Load Sample Data
```bash
# Load sample jobs, students, alumni data
python manage.py loaddata data/csv/
```

### 4. Install ML Dependencies
```bash
pip install sentence-transformers
```

### 5. Run Server
```bash
python manage.py runserver
```

## Cara Kerja Sistem Rekomendasi

### 1. Input Processing
```python
# Data mahasiswa diproses dari form
student_data = {
    'gpa': 3.5,
    'program': 'Computer Science',
    'skills': ['Python', 'Machine Learning']
}
courses = [{'code': 'CS101', 'grade': 'AA'}, ...]
experiences = [{'company': 'Tech Corp', 'position': 'Intern'}, ...]
```

### 2. Alumni Matching Algorithm
```python
def get_alumni_recommendations(student_data, courses, skills):
    # Cari alumni dengan profil serupa
    for alumni in alumni_database:
        # Hitung program bonus
        program_bonus = 1.5 if alumni.program == student.program else 1.0
        
        # Hitung GPA similarity
        gpa_similarity = max(0, 1 - abs(student_gpa - alumni_gpa) / 4.0)
        
        # Hitung course similarity
        course_similarity = calculate_course_overlap(student_courses, alumni_courses)
        
        # Hitung skills bonus
        skill_bonus = calculate_skill_match(student_skills, job_skills)
        
        # Total similarity
        similarity = (0.3 * gpa_similarity + 0.7 * course_similarity) * program_bonus * skill_bonus
```

### 3. Experience-based Matching
```python
def get_job_recommendations(student_data, experiences, skills):
    # Gabungkan semua pengalaman jadi satu teks
    combined_experience = ' '.join([exp.description for exp in experiences])
    
    # Encode menggunakan Sentence-BERT
    experience_embedding = model.encode(combined_experience)
    
    # Hitung similarity dengan setiap job
    for job in job_database:
        job_text = f"{job.title}. {job.description}"
        job_embedding = model.encode(job_text)
        
        # Cosine similarity
        similarity = cosine_similarity(experience_embedding, job_embedding)
        
        # Tambahkan bonus untuk program dan skills match
        total_score = similarity * program_bonus * skill_bonus
```

### 4. Hybrid Combination
```python
def get_hybrid_recommendations(student_data, courses, experiences, skills):
    # Dapat rekomendasi dari kedua sumber
    alumni_recs = get_alumni_recommendations(student_data, courses, skills)
    job_recs = get_job_recommendations(student_data, experiences, skills)
    
    # Kombinasi dengan weighted scoring
    for job in all_jobs:
        final_score = (alumni_score * 0.6) + (experience_score * 0.4)
    
    # Sort dan return top recommendations
    return sorted(recommendations, key=lambda x: x.score, reverse=True)
```

### 5. AI Analysis Integration
```python
def analyze_job_compatibility(student_profile, job_data):
    # Gunakan LLM untuk analisis mendalam
    prompt = f"""
    Analyze compatibility between:
    Student: {student_profile}
    Job: {job_data}
    
    Provide structured analysis on:
    1. Skill match
    2. Experience relevance  
    3. Growth potential
    4. Recommendations
    """
    
    return llm.generate_text(prompt)
```

## Fitur Unggulan

1. **Multi-source Recommendations**: Kombinasi data alumni dan job postings
2. **Machine Learning Integration**: Menggunakan state-of-the-art NLP models
3. **Real-time AI Analysis**: Analisis kompatibilitas menggunakan LLM
4. **Personalized Career Advice**: Saran karir yang disesuaikan dengan profil
5. **Skill Gap Analysis**: Identifikasi dan roadmap pengembangan skill
6. **Scalable Architecture**: Dapat menangani ribuan mahasiswa dan jobs
7. **User-friendly Interface**: Form yang intuitif dan hasil yang mudah dipahami

## Templates dan UI

### Template Structure
```
templates/job_recommender/
├── career_form.html       # Form input profil mahasiswa
├── recommendation_results.html  # Hasil rekomendasi
└── landing_page.html      # Halaman utama
```

### UI Components

#### 1. Career Form (`career_form.html`)
- **Multi-step Form**: Progress indicator dengan 3 tahap
- **PDF Upload**: Support upload transkrip PDF
- **Dynamic Fields**: Form yang adaptif untuk pengalaman dan mata kuliah
- **Real-time Validation**: Validasi input secara langsung
- **Skills Selection**: Dropdown multi-select untuk skills

#### 2. Recommendation Results (`recommendation_results.html`)  
- **Match Score Display**: Visualisasi persentase kesesuaian
- **Source Indicators**: Badge untuk menunjukkan sumber rekomendasi
- **Job Details**: Informasi lengkap posisi dan perusahaan
- **AI Analysis**: Tombol untuk analisis kompatibilitas mendalam

#### 3. Landing Page (`landing_page.html`)
- **Hero Section**: Penjelasan sistem dan call-to-action
- **Feature Overview**: Highlight fitur-fitur utama
- **Statistics**: Metric pencapaian sistem

## Admin Interface

### Django Admin Configuration

#### 1. Student Admin
```python
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'fullname', 'program', 'gpa', 'is_alumni')
    search_fields = ('student_id', 'fullname', 'program')
    list_filter = ('program', 'faculty', 'is_alumni')
    inlines = [AlumniInline, CourseInline, ExperienceInline, JobRecommendationInline]
```

#### 2. Alumni Admin
```python
@admin.register(Alumni)
class AlumniAdmin(admin.ModelAdmin):
    list_display = ('get_student_id', 'get_student_name', 'graduation_date', 'current_company')
    search_fields = ('student__student_id', 'current_company')
    list_filter = ('graduation_date',)
```

#### 3. Job Recommendation Admin
```python
@admin.register(JobRecommendation) 
class JobRecommendationAdmin(admin.ModelAdmin):
    list_display = ('job', 'student', 'match_score', 'source', 'created_at')
    list_filter = ('source', 'created_at')
    readonly_fields = ('created_at',)
```

### Admin Features
- **Inline Editing**: Edit related records dalam satu halaman
- **Search & Filter**: Pencarian dan filter yang komprehensif  
- **Bulk Operations**: Operasi massal untuk efficiency
- **Read-only Fields**: Protection untuk field yang tidak boleh diubah

## Management Commands

### 1. Seed Data Command
```bash
python manage.py seed_data
```

**Fungsi**:
- Import data mahasiswa dari `data/csv/students.csv`
- Import mata kuliah dari `data/csv/courses.csv`
- Import pengalaman dari `data/csv/experiences.csv`
- Import job postings dari `data/csv/jobs.csv`
- Generate alumni records otomatis
- Generate initial job recommendations

**CSV Format**:

#### students.csv
```csv
student_id,id_number,fullname,last_name,birth_date,faculty,program,gpa
20180001,11111111,Ahmad,Rizki,1999-01-15,Engineering,Computer Science,3.75
```

#### courses.csv
```csv
student_id,code,name,grade
20180001,CS101,Programming Fundamentals,AA
20180001,CS102,Data Structures,BA
```

#### experiences.csv
```csv
student_id,experience_type,institution_name,position,start_date,end_date,description
20180001,internship,Tech Corp,Software Intern,2021-06-01,2021-08-31,Backend development
```

#### jobs.csv
```csv
title,company,description,required_majors,required_skills
Software Engineer,Google,"Develop scalable systems","[""Computer Science""]","[""Python"", ""Java""]"
```

## Konfigurasi dan Settings

### 1. Django Settings
```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'job_recommender',
    'utils',  # LLM utilities
]

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... database config
    }
}
```

### 2. Model Dependencies
```python
# Pastikan model relationships benar
REQUIRED_MODELS = [
    'auth.User',           # Django user model
    'job_recommender.Student',
    'job_recommender.Alumni', 
    'job_recommender.Job',
    'job_recommender.Course',
    'job_recommender.Experience',
    'job_recommender.JobRecommendation'
]
```

### 3. External Dependencies
```python
# requirements.txt additions
sentence-transformers==2.2.2
torch>=1.9.0
transformers>=4.21.0
numpy>=1.21.0
scikit-learn>=1.0.0
```

## Testing

### 1. Unit Tests
```bash
python manage.py test job_recommender
```

### 2. Integration Tests
```bash
python manage.py test job_recommender.tests.test_recommender
```

### 3. Performance Tests
```bash
python manage.py test job_recommender.tests.test_performance
```

## Monitoring dan Logging

### 1. Logging Configuration
```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'job_recommender.log',
        },
    },
    'loggers': {
        'job_recommender': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### 2. Performance Metrics
- **Recommendation Generation Time**: < 2 seconds
- **Database Query Optimization**: Using select_related dan prefetch_related
- **Caching**: LLM response caching untuk efisiensi
- **Memory Usage**: Monitoring untuk large datasets

## Troubleshooting

### 1. Common Issues

#### "No recommendations found"
**Penyebab**: Data alumni atau job postings kosong
**Solusi**:
```bash
python manage.py seed_data  # Load sample data
```

#### "Sentence transformer model download failed"
**Penyebab**: Network atau storage issues
**Solusi**:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

#### "LLM integration not working"
**Penyebab**: LLM service configuration
**Solusi**: Check `utils/llm_utils.py` configuration

### 2. Performance Issues

#### Slow recommendation generation
**Optimisasi**:
- Enable database indexing
- Use pagination untuk large datasets
- Implement result caching
- Optimize SQL queries

#### Memory usage too high
**Solusi**:
- Batch processing untuk large datasets
- Clear model cache periodically
- Use streaming untuk file processing

### 3. Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('job_recommender').setLevel(logging.DEBUG)

# Test recommender directly
from job_recommender.recommender import HybridRecommender
recommender = HybridRecommender()
# ... test calls
```

## API Documentation

### 1. Request/Response Examples

#### Submit Application
```bash
curl -X POST /api/submit-application/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "student_id=20180001&fullname=Ahmad&program=Computer Science&gpa=3.75"
```

**Response**:
```json
{
  "status": "success",
  "message": "Application received and saved successfully",
  "data": {
    "student": {...},
    "job_recommendations": [
      {
        "id": 1,
        "title": "Software Engineer",
        "company": "Google",
        "match_score": 85,
        "recommendation_sources": ["alumni", "job_posting"]
      }
    ]
  }
}
```

#### AI Job Compatibility Analysis
```bash
curl -X POST /api/analyze-compatibility/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "student_id=1&job_id=1"
```

**Response**:
```json
{
  "success": true,
  "analysis": {
    "compatibility_score": 8.5,
    "strengths": ["Strong programming background", "Relevant coursework"],
    "gaps": ["Need more system design experience"],
    "recommendations": ["Take distributed systems course", "Build portfolio projects"]
  }
}
```

## Deployment

### 1. Production Setup
```bash
# Install production dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic

# Run migrations
python manage.py migrate

# Seed initial data
python manage.py seed_data

# Start server
gunicorn app.wsgi:application
```

### 2. Docker Deployment
```dockerfile
FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app.wsgi:application"]
```

### 3. Environment Variables
```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key
DEBUG=False
LLM_API_KEY=your-llm-api-key
```

## Contributing

### 1. Development Workflow
1. Fork repository
2. Create feature branch
3. Implement changes dengan tests
4. Submit pull request

### 2. Code Standards
- Follow PEP 8 untuk Python code
- Use type hints where appropriate
- Write comprehensive docstrings
- Add unit tests untuk new features

### 3. Feature Requests
- Open GitHub issue dengan label 'enhancement'
- Provide detailed requirements dan use case
- Include mockups untuk UI changes

## Roadmap

### Phase 1 (Completed) ✅
- [x] Basic recommendation system
- [x] Alumni-based matching
- [x] Experience-based matching
- [x] Web interface
- [x] Admin panel

### Phase 2 (Current)
- [ ] Advanced AI integration
- [ ] Real-time notifications
- [ ] Mobile app support
- [ ] Analytics dashboard

### Phase 3 (Future)
- [ ] Machine learning model training
- [ ] Social features (reviews, ratings)
- [ ] Integration dengan job boards
- [ ] Advanced analytics dan reporting

Sistem ini dirancang untuk membantu mahasiswa membuat keputusan karir yang lebih baik berdasarkan data empiris dari alumni yang sukses dan analisis AI yang canggih.
