# Generated by Django 5.1.7 on 2025-04-06 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("funds", "0011_portfolioweek_net_cost_basis"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundversion",
            name="confidence_shift_percentage",
            field=models.PositiveIntegerField(default=20),
        ),
        migrations.AddField(
            model_name="fundversionallocation",
            name="modifier",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fundversionallocation",
            name="monthly_confidence",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fundversionallocation",
            name="quarterly_confidence",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fundversionallocation",
            name="weekly_confidence",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
