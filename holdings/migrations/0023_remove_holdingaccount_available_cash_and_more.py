# Generated by Django 5.1.7 on 2025-03-30 22:15

import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("holdings", "0022_holdingaccount_portfolio"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="holdingaccount",
            name="available_cash",
        ),
        migrations.CreateModel(
            name="HoldingAccountCash",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=64)),
                (
                    "total",
                    models.DecimalField(
                        decimal_places=4, default=Decimal("0"), max_digits=32
                    ),
                ),
                (
                    "holding_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cash_amounts",
                        to="holdings.holdingaccount",
                    ),
                ),
            ],
        ),
    ]
