# Generated by Django 5.1.7 on 2025-03-23 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("holdings", "0017_holdingaccountaction_has_remaining_quantity_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="holdingaccountaction",
            options={"ordering": ["purchased_on"]},
        ),
        migrations.AlterModelOptions(
            name="holdingaccountgeneration",
            options={"ordering": ["date"]},
        ),
        migrations.AlterModelOptions(
            name="holdingaccountposition",
            options={"ordering": ["ticker_symbol"]},
        ),
        migrations.AlterModelOptions(
            name="holdingaccountsale",
            options={"ordering": ["sale_date"]},
        ),
    ]
