# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.13 on 2020-07-02 04:19
from django.db import migrations
from django.db import models

import leaderboard.models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboard', '0017_submission_is_constrained'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='publication_name',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Team publication name (max 32 characters)',
                max_length=200,
                unique=True,
                validators=[leaderboard.models.validate_team_name],
            ),
        ),
    ]
