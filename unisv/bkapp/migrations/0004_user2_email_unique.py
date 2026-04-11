"""User2.email 改为 unique + 必填，先清空旧账号避免唯一约束冲突。

旧账号是用 username + 空邮箱注册的，无法复用，按用户要求直接清空。
依赖的 MomentumWatch 等外键会随用户删除而级联清理。
"""
from django.db import migrations, models


def wipe_old_users(apps, schema_editor):
    User2 = apps.get_model('bkapp', 'User2')
    # 保留超级管理员，避免登录失败
    User2.objects.filter(is_superuser=False).delete()
    # 给残留的超管补一个占位邮箱
    for u in User2.objects.filter(email=''):
        u.email = f'admin{u.id}@local'
        u.save(update_fields=['email'])


def reverse_noop(apps, schema_editor):
    # 不做反向迁移，旧数据已删除无法恢复
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp', '0003_user2_backtest_quota'),
    ]

    operations = [
        migrations.RunPython(wipe_old_users, reverse_noop),
        migrations.AlterField(
            model_name='user2',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
