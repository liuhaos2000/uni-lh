@echo off
echo Activating virtual environment...
call D:\99_wk\pythondev\myenv\Scripts\activate.bat

echo Starting Celery Worker...
start cmd /k celery -A unisv worker -l INFO -P threads

echo Starting Celery Beat...
start cmd /k celery -A unisv beat -l INFO

echo Starting Django runserver...
start cmd /k python manage.py runserver 0.0.0.0:8000

echo All services started!
