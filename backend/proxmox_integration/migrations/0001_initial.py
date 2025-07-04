# Generated by Django 4.2.7 on 2025-07-03 22:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ProxmoxContainer",
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
                ("vmid", models.IntegerField()),
                ("name", models.CharField(max_length=255)),
                (
                    "type",
                    models.CharField(
                        choices=[("lxc", "LXC Container"), ("qemu", "QEMU VM")],
                        default="lxc",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("stopped", "Stopped"),
                            ("running", "Running"),
                            ("paused", "Paused"),
                            ("template", "Template"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("memory", models.IntegerField(default=2048)),
                ("memory_usage", models.IntegerField(default=0)),
                ("disk_size", models.BigIntegerField(default=8589934592)),
                ("disk_usage", models.BigIntegerField(default=0)),
                ("cores", models.IntegerField(default=2)),
                ("cpu_usage", models.FloatField(default=0.0)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("mac_address", models.CharField(blank=True, max_length=17)),
                ("network_in", models.BigIntegerField(default=0)),
                ("network_out", models.BigIntegerField(default=0)),
                (
                    "template",
                    models.CharField(default="ubuntu-22.04-standard", max_length=255),
                ),
                ("os_type", models.CharField(blank=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("tags", models.CharField(blank=True, max_length=500)),
                ("protection", models.BooleanField(default=False)),
                ("uptime", models.BigIntegerField(default=0)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["vmid"],
            },
        ),
        migrations.CreateModel(
            name="ProxmoxHost",
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
                ("name", models.CharField(max_length=255, unique=True)),
                ("host", models.CharField(max_length=255)),
                ("port", models.IntegerField(default=8006)),
                ("username", models.CharField(max_length=255)),
                ("password", models.CharField(max_length=255)),
                ("realm", models.CharField(default="pam", max_length=50)),
                ("ssl_verify", models.BooleanField(default=False)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "cluster_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("api_version", models.CharField(default="2.0", max_length=20)),
                ("last_seen", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ProxmoxNode",
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
                ("name", models.CharField(max_length=255)),
                ("node_id", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("online", "Online"),
                            ("offline", "Offline"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("cpu_cores", models.IntegerField(default=0)),
                ("cpu_usage", models.FloatField(default=0.0)),
                ("memory_total", models.BigIntegerField(default=0)),
                ("memory_used", models.BigIntegerField(default=0)),
                ("disk_total", models.BigIntegerField(default=0)),
                ("disk_used", models.BigIntegerField(default=0)),
                ("uptime", models.BigIntegerField(default=0)),
                ("kernel_version", models.CharField(blank=True, max_length=255)),
                ("pve_version", models.CharField(blank=True, max_length=100)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nodes",
                        to="proxmox_integration.proxmoxhost",
                    ),
                ),
            ],
            options={
                "ordering": ["host", "name"],
                "unique_together": {("host", "node_id")},
            },
        ),
        migrations.CreateModel(
            name="ProxmoxTask",
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
                ("task_id", models.CharField(max_length=100)),
                ("upid", models.CharField(max_length=200, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("backup", "Backup"),
                            ("restore", "Restore"),
                            ("create", "Create"),
                            ("destroy", "Destroy"),
                            ("start", "Start"),
                            ("stop", "Stop"),
                            ("migrate", "Migrate"),
                            ("clone", "Clone"),
                            ("template", "Template"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("stopped", "Stopped"),
                            ("ok", "OK"),
                            ("error", "Error"),
                            ("warning", "Warning"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("user", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("progress", models.FloatField(default=0.0)),
                ("starttime", models.DateTimeField()),
                ("endtime", models.DateTimeField(blank=True, null=True)),
                ("vmid", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "container",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tasks",
                        to="proxmox_integration.proxmoxcontainer",
                    ),
                ),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="proxmox_integration.proxmoxhost",
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="proxmox_integration.proxmoxnode",
                    ),
                ),
            ],
            options={
                "ordering": ["-starttime"],
            },
        ),
        migrations.AddField(
            model_name="proxmoxcontainer",
            name="host",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="containers",
                to="proxmox_integration.proxmoxhost",
            ),
        ),
        migrations.AddField(
            model_name="proxmoxcontainer",
            name="node",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="containers",
                to="proxmox_integration.proxmoxnode",
            ),
        ),
        migrations.CreateModel(
            name="ProxmoxStorage",
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
                ("storage_id", models.CharField(max_length=100)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("dir", "Directory"),
                            ("nfs", "NFS"),
                            ("cifs", "CIFS/SMB"),
                            ("lvm", "LVM"),
                            ("zfs", "ZFS"),
                            ("cephfs", "CephFS"),
                            ("glusterfs", "GlusterFS"),
                            ("iscsi", "iSCSI"),
                        ],
                        max_length=20,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=500)),
                ("server", models.CharField(blank=True, max_length=255)),
                ("export", models.CharField(blank=True, max_length=500)),
                ("total_space", models.BigIntegerField(default=0)),
                ("used_space", models.BigIntegerField(default=0)),
                ("available_space", models.BigIntegerField(default=0)),
                (
                    "content_types",
                    models.CharField(
                        default="images,vztmpl,iso,backup", max_length=200
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("shared", models.BooleanField(default=False)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="storages",
                        to="proxmox_integration.proxmoxhost",
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="storages",
                        to="proxmox_integration.proxmoxnode",
                    ),
                ),
            ],
            options={
                "ordering": ["storage_id"],
                "unique_together": {("host", "storage_id")},
            },
        ),
        migrations.AlterUniqueTogether(
            name="proxmoxcontainer",
            unique_together={("host", "vmid")},
        ),
    ]
