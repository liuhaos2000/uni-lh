from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MomentumWatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('etf_codes', models.JSONField(default=list)),
                ('lookback_n', models.IntegerField(default=25)),
                ('rebalance_days', models.IntegerField(default=5)),
                ('initial_capital', models.FloatField(default=1000000)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='momentum_watch',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'momentum_watch',
            },
        ),
    ]
