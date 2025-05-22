class LedgerBackupService:
    """Service for backup and restoration of the escalation ledger"""
    
    def __init__(self, config):
        self.config = config
        self.backup_providers = self._init_backup_providers(config.providers)
        
    async def create_backup(self, cutoff_time=None):
        """Create a backup of the ledger up to the specified cutoff time"""
        backup_id = str(uuid.uuid4())
        cutoff = cutoff_time or datetime.utcnow()
        
        backup_metadata = {
            "backup_id": backup_id,
            "created_at": datetime.utcnow().isoformat(),
            "cutoff_time": cutoff.isoformat(),
            "backup_type": "scheduled"
        }
        
        # Create backups with all providers
        results = {}
        for provider_name, provider in self.backup_providers.items():
            try:
                result = await provider.create_backup(
                    backup_id=backup_id,
                    cutoff_time=cutoff,
                    metadata=backup_metadata
                )
                results[provider_name] = {
                    "status": "success",
                    "location": result.location,
                    "size_bytes": result.size_bytes
                }
            except Exception as e:
                results[provider_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Record backup metadata
        backup_record = {
            "backup_id": backup_id,
            "created_at": backup_metadata["created_at"],
            "cutoff_time": backup_metadata["cutoff_time"],
            "provider_results": results,
            "overall_status": "success" if any(r["status"] == "success" for r in results.values()) else "failed"
        }
        
        await self._store_backup_record(backup_record)
        return backup_record
    
    async def restore_from_backup(self, backup_id=None, point_in_time=None):
        """Restore ledger from backup, either by ID or nearest to point in time"""
        # Find appropriate backup to restore from
        if backup_id:
            backup = await self._get_backup_by_id(backup_id)
            if not backup:
                raise BackupError(f"Backup with ID {backup_id} not found")
        elif point_in_time:
            backup = await self._find_nearest_backup(point_in_time)
            if not backup:
                raise BackupError(f"No backup found near point in time {point_in_time}")
        else:
            # Default to latest backup
            backup = await self._get_latest_backup()
            if not backup:
                raise BackupError("No backups available for restoration")
                
        # Find provider with successful backup
        provider_name = None
        for name, result in backup["provider_results"].items():
            if result["status"] == "success":
                provider_name = name
                break
                
        if not provider_name:
            raise BackupError(f"No successful backup found in backup {backup['backup_id']}")
            
        provider = self.backup_providers[provider_name]
        
        # Perform restoration
        try:
            result = await provider.restore_backup(
                backup_id=backup["backup_id"],
                location=backup["provider_results"][provider_name]["location"]
            )
            
            # Record restoration event
            restoration_record = {
                "backup_id": backup["backup_id"],
                "restored_at": datetime.utcnow().isoformat(),
                "provider": provider_name,
                "status": "success",
                "events_restored": result.events_restored
            }
            
            await self._store_restoration_record(restoration_record)
            return restoration_record
        except Exception as e:
            # Record failed restoration attempt
            restoration_record = {
                "backup_id": backup["backup_id"],
                "attempted_at": datetime.utcnow().isoformat(),
                "provider": provider_name,
                "status": "failed",
                "error": str(e)
            }
            
            await self._store_restoration_record(restoration_record)
            raise BackupError(f"Failed to restore from backup: {str(e)}")