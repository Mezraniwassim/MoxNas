# Generated by Django 4.2.7 on 2025-06-24 21:56

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LogEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("DEBUG", "Debug"),
                            ("INFO", "Info"),
                            ("WARNING", "Warning"),
                            ("ERROR", "Error"),
                            ("CRITICAL", "Critical"),
                        ],
                        max_length=10,
                    ),
                ),
                ("service", models.CharField(max_length=50)),
                ("message", models.TextField()),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="ServiceStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("smb", "SMB/CIFS"),
                            ("nfs", "NFS"),
                            ("ftp", "FTP"),
                            ("ssh", "SSH"),
                            ("snmp", "SNMP"),
                            ("iscsi", "iSCSI"),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("running", models.BooleanField(default=False)),
                ("port", models.IntegerField()),
                ("last_checked", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SystemInfo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("hostname", models.CharField(max_length=255)),
                ("version", models.CharField(default="1.0.0", max_length=50)),
                ("uptime", models.IntegerField(default=0)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "System Information",
                "verbose_name_plural": "System Information",
            },
        ),
    ]
