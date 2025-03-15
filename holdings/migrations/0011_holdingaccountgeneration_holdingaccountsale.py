# Generated by Django 5.1.7 on 2025-03-09 19:46

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("holdings", "0010_alter_holdingaccountposition_holding_account"),
    ]

    operations = [
        migrations.CreateModel(
            name="HoldingAccountGeneration",
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
                ("date", models.DateField()),
                (
                    "event",
                    models.CharField(
                        choices=[
                            ("dividend", "Dividend"),
                            ("long-term-cap-gain", "Long Term Cap Gain"),
                            ("short-term-cap-gain", "Short Term Cap Gain"),
                            ("interest", "Interest"),
                            ("royalty-payment", "Royalty Payment"),
                            ("return-of-capital", "Return Of Capital"),
                            ("foreign-tax", "Foreign Tax"),
                            ("fee", "Fee"),
                        ],
                        max_length=32,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=8, max_digits=32)),
                ("cost_basis", models.DecimalField(decimal_places=8, max_digits=32)),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generations",
                        to="holdings.holdingaccountposition",
                    ),
                ),
            ],
            options={
                "unique_together": {("position", "date", "event", "amount")},
            },
        ),
        migrations.CreateModel(
            name="HoldingAccountSale",
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
                ("purchase_date", models.DateField()),
                (
                    "purchase_price",
                    models.DecimalField(decimal_places=8, max_digits=32),
                ),
                ("sale_date", models.DateField()),
                ("sale_price", models.DecimalField(decimal_places=8, max_digits=32)),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sales",
                        to="holdings.holdingaccountposition",
                    ),
                ),
            ],
            options={
                "unique_together": {
                    (
                        "position",
                        "purchase_date",
                        "purchase_price",
                        "sale_date",
                        "sale_price",
                    )
                },
            },
        ),
    ]
