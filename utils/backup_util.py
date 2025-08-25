"""
Backup utility for the RPG bot
"""

import os
import shutil
import schedule
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from database.db_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)


class BackupManager:
    """Manage database backups"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.backup_dir = Path(config.DATABASE_BACKUP_PATH)
        self.ensure_backup_dir()
        self.scheduler_thread = None
        
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Backup directory: {self.backup_dir}")
    
    async def create_backup(self) -> str:
        """Create a database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"game_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # For SQLite database
            if 'sqlite' in self.db.db_path:
                db_file = self.db.db_path.replace('sqlite:///', '')
                shutil.copy2(db_file, backup_path)
                logger.info(f"✅ Backup created: {backup_path}")
                
            # For PostgreSQL (requires pg_dump)
            else:
                import subprocess
                cmd = f"pg_dump {self.db.db_path} > {backup_path.with_suffix('.sql')}"
                subprocess.run(cmd, shell=True, check=True)
                backup_path = backup_path.with_suffix('.sql')
                logger.info(f"✅ PostgreSQL backup created: {backup_path}")
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            raise
    
    def cleanup_old_backups(self):
        """Remove old backup files"""
        import glob
        
        # Get all backup files
        backup_files = list(self.backup_dir.glob("game_backup_*.db"))
        backup_files.extend(self.backup_dir.glob("game_backup_*.sql"))
        
        # Sort by modification time
        backup_files.sort(key=lambda x: x.stat().st_mtime)
        
        # Keep only recent backups
        current_time = time.time()
        keep_days = config.BACKUP_KEEP_DAYS
        
        for backup_file in backup_files:
            file_age_days = (current_time - backup_file.stat().st_mtime) / (24 * 3600)
            
            if file_age_days > keep_days:
                backup_file.unlink()
                logger.info(f"🗑 Deleted old backup: {backup_file.name}")
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from backup"""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        try:
            # For SQLite
            if backup_path.suffix == '.db':
                db_file = self.db.db_path.replace('sqlite:///', '')
                
                # Create backup of current database
                current_backup = f"{db_file}.before_restore"
                shutil.copy2(db_file, current_backup)
                
                # Restore from backup
                shutil.copy2(backup_path, db_file)
                logger.info(f"✅ Database restored from: {backup_file}")
                
            # For PostgreSQL
            elif backup_path.suffix == '.sql':
                import subprocess
                cmd = f"psql {self.db.db_path} < {backup_path}"
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"✅ PostgreSQL database restored from: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return False
    
    def list_backups(self) -> list:
        """List all available backups"""
        backup_files = list(self.backup_dir.glob("game_backup_*"))
        backup_list = []
        
        for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            backup_list.append({
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_mb': round(size_mb, 2),
                'created': modified.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return backup_list
    
    def schedule_backups(self):
        """Schedule automatic backups"""
        if config.BACKUP_INTERVAL_HOURS <= 0:
            logger.info("Automatic backups disabled")
            return
        
        # Schedule backup
        schedule.every(config.BACKUP_INTERVAL_HOURS).hours.do(self._run_scheduled_backup)
        
        # Also schedule daily cleanup at 3 AM
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)
        
        # Start scheduler in separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"✅ Backup scheduler started (every {config.BACKUP_INTERVAL_HOURS} hours)")
    
    def _run_scheduled_backup(self):
        """Run scheduled backup (sync wrapper for async function)"""
        import asyncio
        
        try:
            # Create new event loop for thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run backup
            backup_file = loop.run_until_complete(self.create_backup())
            logger.info(f"✅ Scheduled backup completed: {backup_file}")
            
        except Exception as e:
            logger.error(f"❌ Scheduled backup failed: {e}")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def get_backup_stats(self) -> dict:
        """Get backup statistics"""
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size_mb': 0,
                'latest_backup': None,
                'oldest_backup': None
            }
        
        total_size = sum(b['size_mb'] for b in backups)
        
        return {
            'total_backups': len(backups),
            'total_size_mb': round(total_size, 2),
            'latest_backup': backups[0]['created'] if backups else None,
            'oldest_backup': backups[-1]['created'] if backups else None
        }


# CLI interface for manual backup operations
def main():
    """CLI interface for backup operations"""
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(description='RPG Bot Backup Utility')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'clean', 'stats'],
                       help='Action to perform')
    parser.add_argument('--file', help='Backup file for restore operation')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create database and backup managers
    db = DatabaseManager(config.DATABASE_URL)
    backup_manager = BackupManager(db)
    
    if args.action == 'backup':
        # Create backup
        backup_file = asyncio.run(backup_manager.create_backup())
        print(f"✅ Backup created: {backup_file}")
        
    elif args.action == 'restore':
        # Restore from backup
        if not args.file:
            print("❌ Please specify backup file with --file option")
            return
        
        if backup_manager.restore_backup(args.file):
            print(f"✅ Database restored from: {args.file}")
        else:
            print("❌ Restore failed")
            
    elif args.action == 'list':
        # List backups
        backups = backup_manager.list_backups()
        
        if not backups:
            print("No backups found")
            return
        
        print(f"\n{'Filename':<40} {'Size (MB)':<10} {'Created':<20}")
        print("-" * 70)
        
        for backup in backups:
            print(f"{backup['filename']:<40} {backup['size_mb']:<10} {backup['created']:<20}")
            
    elif args.action == 'clean':
        # Clean old backups
        backup_manager.cleanup_old_backups()
        print("✅ Old backups cleaned")
        
    elif args.action == 'stats':
        # Show backup statistics
        stats = backup_manager.get_backup_stats()
        
        print("\n📊 Backup Statistics")
        print("=" * 30)
        print(f"Total backups: {stats['total_backups']}")
        print(f"Total size: {stats['total_size_mb']} MB")
        print(f"Latest backup: {stats['latest_backup']}")
        print(f"Oldest backup: {stats['oldest_backup']}")


if __name__ == '__main__':
    main()