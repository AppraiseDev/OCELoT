# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.1 on 2020-06-19 06:05
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [('leaderboard', '0007_submission_is_public')]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'is_active',
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text='Is active team?',
                    ),
                ),
                (
                    'is_verified',
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text='Is verified team?',
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        db_index=True,
                        help_text='Team name (max 200 characters)',
                        max_length=200,
                    ),
                ),
                (
                    'email',
                    models.EmailField(
                        db_index=True,
                        help_text='Team email',
                        max_length=200,
                    ),
                ),
                (
                    'token',
                    models.CharField(
                        db_index=True, default='d5fad58bcd', max_length=10
                    ),
                ),
            ],
        )
    ]
