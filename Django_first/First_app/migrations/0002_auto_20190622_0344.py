# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2019-06-22 03:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('First_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('email', models.CharField(max_length=32)),
                ('pwd', models.CharField(max_length=32)),
            ],
        ),
        migrations.RemoveField(
            model_name='tags',
            name='father',
        ),
        migrations.RemoveField(
            model_name='videofragments',
            name='tags',
        ),
        migrations.DeleteModel(
            name='Tags',
        ),
        migrations.DeleteModel(
            name='VideoFragments',
        ),
    ]