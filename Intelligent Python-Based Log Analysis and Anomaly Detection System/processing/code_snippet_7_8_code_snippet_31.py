class LedgerStorageEngine:
    """Storage engine for escalation ledger with strong durability guarantees"""
    
    def __init__(self, config):
        # Primary storage
        self.primary_db = self._init_database(config.primary_db_config)
        
        # Replica configuration
        self.replicas = [
            self._init_database(replica_config) 
            for replica_config in config.replica_configs
        ]
        
        self.cache = LRUCache(max_size=config.cache_size)
        self.metrics = StorageMetrics()
        
    async def store_event(self, event, durability_level=DurabilityLevel.COMMITTED):
        """Store an event with specified durability guarantees"""
        start_time = time.monotonic()
        
        try:
            # Serialize event
            event_data = event.to_dict()
            
            # Store in primary with write concern based on durability level
            write_concern = self._durability_to_write_concern(durability_level)
            result = await self.primary_db.events.insert_one(
                event_data, 
                write_concern=write_concern
            )
            
            # Handle synchronous replication if required
            if durability_level >= DurabilityLevel.REPLICATED:
                await self._replicate_synchronously(event_data)
                
            # Update cache
            self.cache.set(f"event:{event.alert_id}:{event.sequence_id}", event)
            
            # Update metrics
            elapsed = time.monotonic() - start_time
            self.metrics.record_write(elapsed, durability_level)
            
            return result
        except Exception as e:
            self.metrics.record_error("store_event", str(e))
            raise LedgerStorageError(f"Failed to store event: {str(e)}")
    
    async def get_events(self, alert_id, include_data=True, filter_types=None, 
                         max_sequence=None, start_sequence=0):
        """Get events for an alert with filtering options"""
        try:
            # Build query
            query = {"alert_id": alert_id}
            if filter_types:
                query["event_type"] = {"$in": filter_types}
            if max_sequence is not None:
                query["sequence_id"] = {"$lte": max_sequence, "$gte": start_sequence}
            else:
                query["sequence_id"] = {"$gte": start_sequence}
                
            # Projection for data exclusion if needed
            projection = None if include_data else {"data": 0}
            
            # Execute query with index hint
            cursor = self.primary_db.events.find(
                query, 
                projection=projection
            ).hint("alert_id_sequence_idx").sort("sequence_id", 1)
            
            # Convert to event objects
            events = [EscalationEvent.from_dict(doc) for doc in await cursor.to_list(length=None)]
            
            return events
        except Exception as e:
            self.metrics.record_error("get_events", str(e))
            raise LedgerStorageError(f"Failed to retrieve events: {str(e)}")
    
    async def get_latest_event(self, alert_id):
        """Get the latest event for an alert"""
        # Check cache first
        cache_key = f"latest_event:{alert_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        # Query database
        try:
            latest = await self.primary_db.events.find_one(
                {"alert_id": alert_id},
                sort=[("sequence_id", -1)]
            )
            
            if not latest:
                return None
                
            event = EscalationEvent.from_dict(latest)
            
            # Update cache
            self.cache.set(cache_key, event)
            
            return event
        except Exception as e:
            self.metrics.record_error("get_latest_event", str(e))
            raise LedgerStorageError(f"Failed to retrieve latest event: {str(e)}")