# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-08-01 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('senders', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sender',
            options={'managed': True, 'ordering': ('email',)},
        ),
        migrations.RemoveField(
            model_name='sender',
            name='password',
        ),
        migrations.AddField(
            model_name='sender',
            name='google_oauth2_client_id',
            field=models.CharField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='sender',
            name='google_oauth2_secrete',
            field=models.CharField(blank=True, default='', max_length=254),
        ),
    ]
