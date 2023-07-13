# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.13 on 2020-07-10 22:45
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('leaderboard', '0020_auto_20200710_2145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='file_format',
            field=models.CharField(
                choices=[('SGML', 'SGML format'), ('TEXT', 'Text format')],
                default='TEXT',
                max_length=4,
            ),
        ),
    ]
