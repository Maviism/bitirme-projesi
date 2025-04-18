## run django
1. create virtual env
```
python -m venv venv
```
2. activate virtual venv
```
# windows
.\venv\Scripts\activate
# linux
source venv/bin/activate
```
3. install django
```
pip install django
```
4. create django project
```
django-admin startproject [project_name]
```
5. run django server
```
cd [project_name]
python manage.py runserver
```


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

