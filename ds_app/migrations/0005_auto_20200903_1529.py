# Generated by Django 3.0.8 on 2020-09-03 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ds_app', '0004_auto_20200728_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpoint',
            name='connection_name',
            field=models.CharField(choices=[('default', 'default'), ('web_cache', 'web_cache'), ('enterprise_data', 'enterprise_data'), ('eva', 'eva'), ('events', 'events'), ('publications', 'publications'), ('web', 'web')], max_length=255),
        ),
    ]