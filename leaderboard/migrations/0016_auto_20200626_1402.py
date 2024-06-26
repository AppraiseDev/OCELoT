# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.13 on 2020-06-26 21:02
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('leaderboard', '0015_auto_20200626_1341'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='is_flagged',
            field=models.BooleanField(
                db_index=True, default=False, help_text='Is flagged?'
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='is_removed',
            field=models.BooleanField(
                db_index=True, default=False, help_text='Is removed?'
            ),
        ),
    ]
