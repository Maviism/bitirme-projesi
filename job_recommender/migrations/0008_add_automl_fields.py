from django.db import migrations, models
import json

class Migration(migrations.Migration):

    dependencies = [
        ('job_recommender', '0007_mlmodelinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='mlmodelinfo',
            name='algorithm',
            field=models.CharField(blank=True, max_length=100, null=True, help_text='The algorithm used by AutoML (e.g., lgbm, xgboost)'),
        ),
        migrations.AddField(
            model_name='mlmodelinfo',
            name='hyperparameters',
            field=models.TextField(blank=True, null=True, help_text='JSON string of hyperparameters'),
        ),
        migrations.AddField(
            model_name='mlmodelinfo',
            name='train_score',
            field=models.FloatField(blank=True, null=True, help_text='Training score of the model'),
        ),
        migrations.AddField(
            model_name='mlmodelinfo',
            name='test_score',
            field=models.FloatField(blank=True, null=True, help_text='Testing score of the model'),
        ),
        migrations.AddField(
            model_name='mlmodelinfo',
            name='metrics',
            field=models.CharField(blank=True, max_length=50, null=True, help_text='Metrics used for evaluation (e.g., f1, accuracy)'),
        ),
        migrations.AddField(
            model_name='mlmodelinfo',
            name='training_time',
            field=models.FloatField(blank=True, null=True, help_text='Time taken to train the model in seconds'),
        ),
        migrations.AlterField(
            model_name='mlmodelinfo',
            name='model_type',
            field=models.CharField(choices=[('alumni', 'Alumni Model'), ('job', 'Job Model'), ('automl', 'AutoML Model')], max_length=20),
        ),
    ]
