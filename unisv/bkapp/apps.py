from django.apps import AppConfig
import os

class BkappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bkapp'

    def ready(self):
        # 防止 runserver 执行两次
        if os.environ.get('RUN_MAIN') != 'true':
            return

        # 预加载（不是必须）
        from .global_data import get_allskname_fromapi_global
        try:
            get_allskname_fromapi_global()
        except Exception as e:
            # 启动阶段不要让 Django 挂掉
            print("API preload failed:", e)