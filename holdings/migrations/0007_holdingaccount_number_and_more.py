# Generated by Django 5.1.7 on 2025-03-08 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("holdings", "0006_holdingaccountalias"),
    ]

    operations = [
        migrations.AddField(
            model_name="holdingaccount",
            name="number",
            field=models.CharField(default="ChangeMe", max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="holdingaccountdocument",
            name="document_type",
            field=models.CharField(
                choices=[("statement", "Statement"), ("activity", "Activity")],
                default="activity",
                max_length=16,
            ),
        ),
    ]
