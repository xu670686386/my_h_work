# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2019-06-23 10:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('First_app', '0002_auto_20190622_0344'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tags',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default=None, max_length=64, null=True, unique=True)),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('update_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256, null=True)),
                ('father', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='First_app.Tags', verbose_name='\u4e0a\u7ea7\u6807\u7b7e')),
            ],
        ),
        migrations.CreateModel(
            name='VideoFragments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('origin_asset_id', models.IntegerField(db_index=True, default=0)),
                ('origin_asset_key', models.CharField(default=None, max_length=64, null=True)),
                ('create_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('update_at', models.DateTimeField(auto_now=True)),
                ('status', models.IntegerField(default=0)),
                ('offset', models.IntegerField(default=0)),
                ('duration', models.IntegerField(default=0)),
                ('file_size', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('video_fragment_url', models.CharField(default=None, max_length=1024, null=True)),
                ('video_fragment_cover_url', models.CharField(default=None, max_length=1024, null=True)),
                ('fragment_duration', models.IntegerField(default=0)),
                ('fragment_asset_key', models.CharField(default=None, max_length=64, null=True)),
                ('desc', models.TextField(default=None, null=True)),
                ('title', models.CharField(default=None, max_length=256, null=True)),
                ('deleted', models.BooleanField(default=False)),
                ('profile_id', models.IntegerField(db_index=True, default=0)),
                ('worker_id', models.IntegerField(default=0)),
                ('tags', models.ManyToManyField(to='First_app.Tags')),
            ],
        ),
        migrations.DeleteModel(
            name='User',
        ),
    ]
