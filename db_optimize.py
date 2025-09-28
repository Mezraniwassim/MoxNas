#!/usr/bin/env python3
"""
Database Performance Optimization Script for MoxNAS
Analyzes and optimizes database performance
"""
import os
import sys
from datetime import datetime, timedelta
from app import create_app, db
from app.models import *
from sqlalchemy import text, inspect
import time

def analyze_query_performance():
    """Analyze slow queries and suggest optimizations"""
    app = create_app()
    
    with app.app_context():
        print("📊 Database Performance Analysis")
        print("=" * 50)
        
        # Check database size
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            result = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY size_bytes DESC
            """))
            
            print("\n📈 Table Sizes:")
            for row in result:
                print(f"  {row.tablename}: {row.size}")
        
        # Check index usage
        print("\n🔍 Index Analysis:")
        inspector = inspect(db.engine)
        for table_name in inspector.get_table_names():
            indexes = inspector.get_indexes(table_name)
            print(f"  {table_name}: {len(indexes)} indexes")
            for idx in indexes:
                print(f"    - {idx['name']}: {idx['column_names']}")
        
        # Check for missing indexes on foreign keys
        print("\n⚠️  Foreign Key Index Analysis:")
        for table_name in inspector.get_table_names():
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            index_columns = set()
            for idx in indexes:
                index_columns.update(idx['column_names'])
            
            for fk in foreign_keys:
                for col in fk['constrained_columns']:
                    if col not in index_columns:
                        print(f"  ⚠️  Missing index on {table_name}.{col}")

def optimize_database():
    """Apply database optimizations"""
    app = create_app()
    
    with app.app_context():
        print("\n🔧 Applying Database Optimizations")
        print("=" * 50)
        
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            # Analyze tables for better query planning
            print("📊 Analyzing tables...")
            db.session.execute(text("ANALYZE;"))
            
            # Vacuum for space reclamation
            print("🧹 Vacuuming tables...")
            db.session.execute(text("VACUUM ANALYZE;"))
            
            # Check for bloated tables
            print("📏 Checking table bloat...")
            result = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    ROUND(CASE WHEN otta=0 THEN 0.0 ELSE sml.relpages/otta::numeric END,1) AS tbloat,
                    CASE WHEN relpages < otta THEN 0 ELSE relpages::bigint - otta END AS wastedpages,
                    CASE WHEN relpages < otta THEN 0 ELSE bs*(sml.relpages-otta)::bigint END AS wastedbytes,
                    CASE WHEN relpages < otta THEN 0 ELSE (bs*(relpages-otta))::bigint END AS wastedsize
                FROM (
                    SELECT 
                        schemaname, tablename, cc.reltuples, cc.relpages, bs,
                        CEIL((cc.reltuples*((datahdr+ma-
                            (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS otta
                    FROM (
                        SELECT 
                            ma,bs,schemaname,tablename,
                            (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
                            (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
                        FROM (
                            SELECT 
                                schemaname, tablename, hdr, ma, bs,
                                SUM((1-null_frac)*avg_width) AS datawidth,
                                MAX(null_frac) AS maxfracsum,
                                hdr+(
                                    SELECT 1+count(*)/8
                                    FROM pg_stats s2
                                    WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
                                ) AS nullhdr
                            FROM pg_stats s, (
                                SELECT 
                                    (SELECT current_setting('block_size')::numeric) AS bs,
                                    CASE WHEN substring(v,12,3) IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
                                    CASE WHEN v ~ 'mingw32' THEN 8 ELSE 4 END AS ma
                                FROM (SELECT version() AS v) AS foo
                            ) AS constants
                            WHERE schemaname='public'
                            GROUP BY 1,2,3,4,5
                        ) AS foo
                    ) AS rs
                    JOIN pg_class cc ON cc.relname = rs.tablename
                    JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = rs.schemaname AND nn.nspname <> 'information_schema'
                ) AS sml
                WHERE sml.relpages - otta > 0
                ORDER BY wastedbytes DESC
            """))
            
            for row in result:
                if row.tbloat > 1.2:  # More than 20% bloat
                    print(f"  ⚠️  {row.tablename}: {row.tbloat}x bloated, {row.wastedsize} bytes wasted")
        
        db.session.commit()
        print("✅ Database optimization complete")

def create_maintenance_indexes():
    """Create additional performance indexes"""
    app = create_app()
    
    with app.app_context():
        print("\n📈 Creating Performance Indexes")
        print("=" * 50)
        
        # Composite indexes for common queries
        indexes_to_create = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_logs_category_level ON system_logs(category, level);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_logs_timestamp_user ON system_logs(timestamp, user_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_storage_devices_pool_status ON storage_devices(pool_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_shares_protocol_status ON shares(protocol, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_jobs_status_schedule ON backup_jobs(status, next_run);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_active_severity ON alerts(is_active, severity);"
        ]
        
        for index_sql in indexes_to_create:
            try:
                print(f"Creating index: {index_sql.split('ON')[1].split('(')[0].strip()}")
                db.session.execute(text(index_sql))
                db.session.commit()
            except Exception as e:
                print(f"  ⚠️  Index creation failed: {e}")
                db.session.rollback()
        
        print("✅ Performance indexes created")

def generate_performance_report():
    """Generate comprehensive performance report"""
    app = create_app()
    
    with app.app_context():
        print("\n📋 Performance Report")
        print("=" * 50)
        
        # Count records in major tables
        tables_to_check = [
            (User, 'users'),
            (StorageDevice, 'storage_devices'),
            (StoragePool, 'storage_pools'),
            (Dataset, 'datasets'),
            (Share, 'shares'),
            (BackupJob, 'backup_jobs'),
            (SystemLog, 'system_logs'),
            (Alert, 'alerts')
        ]
        
        print("📊 Record Counts:")
        for model, name in tables_to_check:
            count = model.query.count()
            print(f"  {name}: {count:,} records")
        
        # Check for old log entries
        old_logs = SystemLog.query.filter(
            SystemLog.timestamp < datetime.utcnow() - timedelta(days=90)
        ).count()
        
        if old_logs > 0:
            print(f"\n🗑️  Found {old_logs:,} log entries older than 90 days")
            print("   Consider implementing log rotation")
        
        # Check backup job efficiency
        failed_backups = BackupJob.query.filter(
            BackupJob.status == BackupStatus.FAILED
        ).count()
        
        total_backups = BackupJob.query.count()
        if total_backups > 0:
            success_rate = ((total_backups - failed_backups) / total_backups) * 100
            print(f"\n💾 Backup Success Rate: {success_rate:.1f}%")
            if success_rate < 95:
                print("   ⚠️  Consider reviewing failed backup configurations")

if __name__ == '__main__':
    analyze_query_performance()
    optimize_database()
    create_maintenance_indexes()
    generate_performance_report()
    print("\n✅ Database maintenance complete!")
