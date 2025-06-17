# LLM Utils - Quick Reference

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install openai google-generativeai

# 2. Set up .env
cp .env.example .env
# Edit .env with your API keys

# 3. Test connection
python manage.py test_llm --provider openai
```

## 📝 Resume Generator

```python
from utils.llm_utils import get_llm_instance
from resume_generator.utils import generate_resume_content

llm = get_llm_instance()
resume = generate_resume_content(llm, user_data, job_description)
```

**AJAX Endpoint:**
```javascript
fetch('/resume_generator/ai/generate/', {
    method: 'POST',
    body: formData
}).then(r => r.json()).then(data => console.log(data.content));
```

## 🎯 Job Compatibility

```python
compatibility = llm.analyze_job_compatibility(user_profile, job_data)
print(f"Match: {compatibility['compatibility_score']}%")
```

**AJAX Endpoint:**
```javascript
fetch('/job_recommender/ai/analyze/', {
    method: 'POST',
    body: formData
}).then(r => r.json()).then(data => console.log(data.analysis));
```

## 💡 Other Functions

```python
# Improve text
from resume_generator.utils import improve_resume_section
improved = improve_resume_section(llm, content, section_type, context)

# Generate cover letter
from resume_generator.utils import generate_cover_letter_content
letter = generate_cover_letter_content(llm, user_data, job_data)

# Get recommendations
recs = llm.generate_job_recommendations(profile, jobs)
```

## ⚡ Available Endpoints

| Endpoint | Purpose | App |
|----------|---------|-----|
| `/resume_generator/ai/generate/` | Generate AI resume | resume_generator |
| `/resume_generator/ai/improve/` | Improve section | resume_generator |
| `/resume_generator/ai/cover-letter/` | Generate cover letter | resume_generator |
| `/job_recommender/ai/analyze/` | Job compatibility | job_recommender |
| `/job_recommender/ai/recommend/` | Job recommendations | job_recommender |

## 🔧 Configuration

```python
# settings.py
DEFAULT_LLM_PROVIDER = 'openai'  # or 'gemini'
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
```

## 💰 Cost Optimization

- ✅ Auto-caching (1 hour)
- ✅ Token limits
- ✅ Error handling
- ⚠️ Monitor API usage

## 🐛 Troubleshooting

```bash
# Test LLM connection
python manage.py test_llm

# Check logs
tail -f logs/django.log | grep llm_utils
```
