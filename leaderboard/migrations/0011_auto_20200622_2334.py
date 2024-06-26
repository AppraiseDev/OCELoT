# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.13 on 2020-06-23 06:34
from django.db import migrations
from django.db import models

import leaderboard.models


class Migration(migrations.Migration):
    dependencies = [('leaderboard', '0010_testset_is_active')]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='name',
            field=models.CharField(
                db_index=True,
                help_text='Team name (max 32 characters)',
                max_length=200,
                unique=True,
                validators=[leaderboard.models.validate_team_name],
            ),
        ),
        migrations.AlterField(
            model_name='team',
            name='token',
            field=models.CharField(
                blank=True, db_index=True, max_length=10, unique=True
            ),
        ),
    ]
