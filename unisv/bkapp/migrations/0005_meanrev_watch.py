from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp', '0004_user2_email_unique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MeanrevWatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('etf_codes', models.JSONField(default=list)),
                ('signal_type', models.CharField(default='bollinger', max_length=20)),
                ('period', models.IntegerField(default=20)),
                ('num_std', models.FloatField(default=2.0)),
                ('oversold', models.IntegerField(default=30)),
                ('overbought', models.IntegerField(default=70)),
                ('stop_loss', models.FloatField(default=0.05)),
                ('rebalance_days', models.IntegerField(default=1)),
                ('initial_capital', models.FloatField(default=1000000)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meanrev_watch',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'meanrev_watch',
            },
        ),
    ]
