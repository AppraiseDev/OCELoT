# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.1 on 2020-06-19 05:29
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [('leaderboard', '0006_auto_20200618_2204')]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='is_public',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Is publicly visible?',
            ),
        )
    ]
