from __future__ import absolute_import, unicode_literals
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unisv.settings')

app = Celery('unisv')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks([
    'bkapp.tasks.update_stock_data',
    'bkapp.tasks.momentum_signal',
])