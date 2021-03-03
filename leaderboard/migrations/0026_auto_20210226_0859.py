# pylint: disable=invalid-name,missing-docstring
# Generated by Django 3.1.7 on 2021-02-26 08:59
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboard', '0025_auto_20210225_1954'),
    ]

    operations = [
        migrations.AddField(
            model_name='competition',
            name='is_public',
            field=models.BooleanField(
                blank=True,
                db_index=True,
                default=None,
                help_text='Are submissions publicly visible? Overwrites settings in test sets and submissions unless Unknown',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='testset',
            name='is_public',
            field=models.BooleanField(
                blank=True,
                db_index=True,
                default=None,
                help_text='Are submissions publicly visible? Overwrite settings from submissions unless Unknown',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='submission',
            name='is_public',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Is publicly visible? Can be overwritten by settings of the test set or competition',
            ),
        ),
    ]
