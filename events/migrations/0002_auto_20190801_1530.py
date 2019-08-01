# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-08-01 15:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='event',
            name='summary',
            field=models.CharField(blank=True, default='', max_length=254),
        ),
    ]
