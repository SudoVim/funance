# Generated by Django 5.1.7 on 2025-04-04 11:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("funds", "0008_portfolio_fund_portfolio"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundversion",
            name="portfolio_shares",
            field=models.PositiveIntegerField(default=1000),
        ),
        migrations.AddField(
            model_name="portfolio",
            name="shares",
            field=models.PositiveIntegerField(default=10000),
        ),
    ]
