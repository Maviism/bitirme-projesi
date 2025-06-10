# ML Model for Job Recommender

This module provides functionality to generate and store ML models for the job recommendation system. 
Instead of querying the database each time recommendations are needed, the system can use pre-generated models 
for better performance.

## Features

- Generate ML models from the current database data
- Store models as pickled files with timestamps
- Load models for use in the recommender system
- Admin interface to trigger model generation

## Usage

### From Admin Interface

1. Go to the admin panel at `/admin/job_recommender/mlmodel/`
2. Click "Generate ML Models"
3. Select the type of model you want to generate (Alumni, Job, or All)
4. Click "Generate Models"

### From Command Line

```bash
python manage.py generate_ml_models --model=all
```

Options for `--model`:
- `all`: Generate both alumni and job models (default)
- `alumni`: Generate only alumni model
- `job`: Generate only job model

## Model Location

Generated models are stored in the `job_recommender/ml_model/stored_models` directory. Each model is timestamped, and a symbolic link named `*_latest.pkl` points to the most recent model.

## Implementation

The recommender system automatically tries to use the latest model first. If the model is not available or cannot be loaded, it falls back to database queries.
