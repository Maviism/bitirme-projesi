# AutoML Job Recommender

This module enhances the job recommendation system by integrating FLAML (Fast and Lightweight AutoML) for automated machine learning model selection and tuning.

## Overview

The AutoML Job Recommender simplifies the recommendation algorithm by:

1. Removing complex manual bonus calculations and weights
2. Automatically finding the best ML model for the specific dataset
3. Providing more accurate predictions with minimal configuration

## Components

- `AlumniAutoMLRecommender`: Core AutoML-based recommendation engine
- Integration with existing hybrid recommendation system
- Management commands for model generation
- Demo script to test the system

## Usage

### Generating Models

Generate the AutoML model with the management command:

```bash
python manage.py generate_automl_model --time-budget 300 --metric f1
```

Options:
- `--time-budget`: Time (in seconds) allocated for model training (default: 300)
- `--metric`: Evaluation metric ('f1', 'accuracy', etc.) (default: 'f1')
- `--no-ensemble`: Disable ensemble models if specified

### Using the Recommender

The recommendation system now exclusively uses AutoML for alumni recommendations:

```python
from job_recommender.recommender import HybridRecommender

# Create recommender - AutoML is now the only option for alumni recommendations
recommender = HybridRecommender(alumni_weight=0.7, job_weight=0.3)

# Get recommendations
recommendations = recommender.get_hybrid_recommendations(
    student_data=student_data,
    courses=courses,
    orgs=orgs,
    internships=internships,
    top_n=10,
    skills=['python', 'machine-learning']  # Optional: filter by skills
)
```

## Model Tracking

The system now tracks detailed model metadata for better analysis and evaluation:

### Stored Metadata

For each AutoML model, the system now tracks:

- **Algorithm**: The best algorithm selected by FLAML (e.g., 'lgbm', 'xgboost')
- **Hyperparameters**: The optimized hyperparameters for the selected algorithm
- **Train Score**: The model's performance score on training data
- **Test Score**: The model's performance score on test data
- **Metrics**: The evaluation metric used (e.g., 'f1', 'accuracy')
- **Training Time**: How long the model took to train (in seconds)

### Accessing Model Metadata

You can access model metadata through the Django ORM:

```python
from job_recommender.models import MLModelInfo

# Get the currently active AutoML model
active_model = MLModelInfo.objects.filter(model_type='automl', is_active=True).first()

# Access metadata
algorithm = active_model.algorithm
test_score = active_model.test_score
hyperparameters = json.loads(active_model.hyperparameters)  # Parse JSON string
```

### Admin Interface

The Django admin interface provides an enhanced view of model metadata, including:

- A formatted display of model hyperparameters
- Filter and search capabilities for models
- Performance metrics for easy comparison

## Performance Analysis

The addition of model metadata tracking enables better analysis of model performance:

1. Compare different AutoML runs to identify trends
2. Monitor how model performance changes as the dataset grows
3. Identify which algorithms perform best for your specific data
4. Track training time to optimize computational resources
