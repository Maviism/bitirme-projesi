## dev environment
1. ubuntu 24.04
2. python 3.12.3

## run django
1. clone the repo
```
git clone [repository_url]
```
2. create virtual environment
```
python -m venv env
```
3. activate virtual environment
```
# Windows
.\env\Scripts\activate
# Linux
source env/bin/activate
```
4. install requirements
```
pip install -r requirements.txt
```
5. create superuser
```
python manage.py createsuperuser
```
6. migrate database
```
python manage.py migrate
```
7. run server
```
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

## Libraries
1. install libraries
```
pip install [library_name]
```
2. add libraries to requirements.txt
```
pip freeze > requirements.txt
```
