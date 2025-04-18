## App

1. add app using cmd line
```
./manage.py startapp [names]
```
2. insert new app to app/settings.py
```python
INSTALLED_APPS = [
    ...
    'app_name',
]
```
3. add app urls to project urls.py
```python
url_patterns = [
    ...
    path('app_name/', include('app_name.urls')),
]
```

