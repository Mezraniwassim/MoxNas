import os
from app.models import (
    StoragePool,
    StorageDevice,
    Dataset,
    PoolStatus,
    DeviceStatus,
    SystemLog,
    LogLevel,
)
from app import db
from datetime import datetime
from typing import Optional


def create_zfs_pool_database_entry(config):
    """Create database entry for ZFS pool"""
    pool = StoragePool(
        name=config.name,
        raid_level=f"zfs_{config.pool_type.value}",
        filesystem_type="zfs",
        mount_point=f"/{config.name}",
        status=PoolStatus.HEALTHY,
        created_at=datetime.utcnow(),
    )

    db.session.add(pool)
    db.session.flush()

    # Add devices
    for device_path in config.devices:
        device = StorageDevice(
            device_path=device_path,
            device_name=os.path.basename(device_path),
            pool_id=pool.id,
            status=DeviceStatus.HEALTHY,
        )
        db.session.add(device)

    db.session.commit()


def create_zfs_dataset_database_entry(config, pool_id):
    """Create database entry for ZFS dataset"""
    dataset = Dataset(
        name=config.name,
        path=config.mount_point or f"/{config.pool_name}/{config.name}",
        pool_id=pool_id,
        created_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.commit()


def get_pool_id(pool_name: str) -> Optional[int]:
    """Get pool ID from database"""
    pool = StoragePool.query.filter_by(name=pool_name).first()
    return pool.id if pool else None
