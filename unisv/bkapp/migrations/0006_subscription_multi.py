from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp', '0005_meanrev_watch'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # MomentumWatch: OneToOne -> ForeignKey, add name
        migrations.AlterField(
            model_name='momentumwatch',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='momentum_watches',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='momentumwatch',
            name='name',
            field=models.CharField(default='', max_length=50),
        ),

        # MeanrevWatch: OneToOne -> ForeignKey, add name
        migrations.AlterField(
            model_name='meanrevwatch',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='meanrev_watches',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='meanrevwatch',
            name='name',
            field=models.CharField(default='', max_length=50),
        ),
    ]
