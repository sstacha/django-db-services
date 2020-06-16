# Generated by Django 3.0.7 on 2020-06-10 21:06

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Endpoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('connection_name', models.CharField(choices=[('default', 'default'), ('publications', 'publications'), ('web_cache', 'web_cache'), ('events', 'events'), ('web', 'web'), ('enterprise_data', 'enterprise_data')], max_length=255)),
                ('path', models.CharField(max_length=800, unique=True)),
                ('get_statement', models.TextField(blank=True, max_length=2000, null=True)),
                ('post_statement', models.TextField(blank=True, max_length=2000, null=True)),
                ('put_statement', models.TextField(blank=True, max_length=2000, null=True)),
                ('delete_statement', models.TextField(blank=True, max_length=2000, null=True)),
                ('notes', models.TextField(blank=True, max_length=2000, null=True)),
                ('is_disabled', models.BooleanField(default=False)),
            ],
        ),
    ]
