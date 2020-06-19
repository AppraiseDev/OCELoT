# Generated by Django 2.2.1 on 2020-06-19 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('leaderboard', '0008_team')]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='date_created',
            field=models.DateTimeField(
                auto_now_add=True,
                help_text='Creation date of this submission',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='submission',
            name='name',
            field=models.CharField(
                db_index=True,
                help_text='Submission name (max 200 characters)',
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name='team',
            name='token',
            field=models.CharField(
                blank=True, db_index=True, max_length=10
            ),
        ),
    ]
