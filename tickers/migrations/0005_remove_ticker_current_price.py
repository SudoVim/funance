# Generated by Django 5.1.7 on 2025-03-29 12:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tickers", "0004_alter_ticker_symbol"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ticker",
            name="current_price",
        ),
    ]
