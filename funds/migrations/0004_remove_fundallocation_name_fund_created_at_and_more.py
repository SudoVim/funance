# Generated by Django 4.2.4 on 2023-08-19 16:11

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("funds", "0003_remove_fund_available_cash_remove_fund_currency_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="fundallocation",
            name="name",
        ),
        migrations.AddField(
            model_name="fund",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="fund",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
