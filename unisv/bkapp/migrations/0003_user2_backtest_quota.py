from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp', '0002_momentum_watch'),
    ]

    operations = [
        migrations.AddField(
            model_name='user2',
            name='backtest_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user2',
            name='backtest_quota',
            field=models.IntegerField(default=20),
        ),
    ]
