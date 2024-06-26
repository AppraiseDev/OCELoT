# pylint: disable=invalid-name,missing-docstring
# Generated by Django 2.2.1 on 2020-06-19 04:57
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [('leaderboard', '0004_auto_20190831_0113')]

    operations = [
        migrations.RemoveField(model_name='testset', name='json_data'),
        migrations.AddField(
            model_name='testset',
            name='sgml_file',
            field=models.FileField(
                help_text='SGML file containing test set',
                null=True,
                upload_to='testsets',
            ),
        ),
        migrations.AddField(
            model_name='testset',
            name='source_language',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='source_language_set',
                to='leaderboard.Language',
            ),
        ),
        migrations.AddField(
            model_name='testset',
            name='target_language',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='target_language_set',
                to='leaderboard.Language',
            ),
        ),
    ]
