# Generated by Django 5.1.7 on 2025-03-29 12:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("holdings", "0020_holdingaccountposition_holdings_ho_quantit_b285f9_idx"),
        ("tickers", "0005_remove_ticker_current_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="holdingaccountposition",
            name="ticker",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="holding_account_positions",
                to="tickers.ticker",
            ),
        ),
    ]
