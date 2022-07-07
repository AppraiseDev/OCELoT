# Generated by Django 3.1.7 on 2022-07-06 17:13
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboard', '0031_auto_20210616_0934'),
    ]

    operations = [
        migrations.AddField(
            model_name='testset',
            name='collection',
            field=models.CharField(
                blank=True,
                help_text='Optional collection name (max 200 characters)',
                max_length=200,
                null=True,
            ),
        ),
    ]