# Generated by Django 3.0.7 on 2020-06-30 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ds_app', '0002_auto_20200611_1848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpoint',
            name='connection_name',
            field=models.CharField(choices=[('default', 'default'), ('web_cache', 'web_cache'), ('enterprise_data', 'enterprise_data'), ('eva', 'eva')], max_length=255),
        ),
    ]
