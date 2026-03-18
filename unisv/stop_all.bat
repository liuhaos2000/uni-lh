@echo off
echo Killing Django, Celery Worker and Beat...
taskkill /F /IM python.exe
taskkill /F /IM celery.exe
echo Done!
