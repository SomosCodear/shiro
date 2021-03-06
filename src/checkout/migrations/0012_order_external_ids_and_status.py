# Generated by Django 3.0.3 on 2020-02-18 01:16

from django.db import migrations, models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('checkout', '0011_orderitemoption_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='external_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='preference_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=model_utils.fields.StatusField(choices=[(0, 'dummy')], default='CREATED', max_length=100, no_check_for_status=True),
        ),
    ]
