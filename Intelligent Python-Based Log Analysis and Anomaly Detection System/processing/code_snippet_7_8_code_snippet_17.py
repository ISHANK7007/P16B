class RoutingOrchestrator:
    def __init__(self, config, team_registry):
        self.config = config
        self.team_registry = team_registry
        self.correlation_store = AlertCorrelationStore()
        self.path_tracker = MultiPathTracker()
        self.routing_evaluator = RoutingRuleEvaluator()
    
    async def route_alert(self, alert_envelope):
        """Orchestrate routing of alert to multiple teams/channels"""
        # Preserve original alert but create routing identifier
        correlation_id = str(uuid.uuid4())
        alert_envelope.add_extension("correlation_id", correlation_id)
        
        # Identify target teams based on alert context
        routing_paths = await self._determine_routing_paths(alert_envelope)
        
        # Create a routing context record to track cross-team handling
        context_record = RoutingContextRecord(
            correlation_id=correlation_id,
            original_alert=alert_envelope,
            paths=routing_paths,
            created_at=datetime.utcnow()
        )
        await self.correlation_store.store_context(context_record)
        
        # Process each path in parallel
        routing_tasks = []
        for path in routing_paths:
            routing_tasks.append(self._process_routing_path(path, alert_envelope, correlation_id))
        
        # Execute routing (non-blocking)
        asyncio.create_task(self._execute_routing(routing_tasks, context_record))
        
        # Return correlation ID for tracking
        return correlation_id
    
    async def _determine_routing_paths(self, alert_envelope):
        """Identify all teams/channels that should receive this alert"""
        paths = []
        anomaly = alert_envelope.anomaly
        
        # Apply routing rules to determine target teams
        routing_rules = self.routing_evaluator.get_applicable_rules(anomaly)
        
        for rule in routing_rules:
            # Evaluate if rule conditions match
            if await rule.evaluate(alert_envelope):
                # Extract team info from rule
                teams = rule.get_target_teams()
                
                # Create routing paths for each team
                for team in teams:
                    team_info = self.team_registry.get_team(team)
                    path = RoutingPath(
                        team_id=team,
                        channels=team_info.channels,
                        priority=rule.get_priority_for_team(team),
                        context_scope=rule.get_context_scope_for_team(team),
                        escalation_policy=team_info.escalation_policy
                    )
                    paths.append(path)
        
        # Handle correlated anomaly classes that may require additional teams
        if anomaly.type == AnomalyType.SECURITY and "database" in anomaly.details.get("affected_systems", []):
            # Special case: Security issues affecting databases need both teams
            security_team = self.team_registry.get_team("security")
            db_team = self.team_registry.get_team("database")
            
            paths.append(RoutingPath(
                team_id="security",
                channels=security_team.channels,
                priority=alert_envelope.anomaly.criticality.value,
                context_scope={"security_perspective": True},
                escalation_policy=security_team.escalation_policy
            ))
            
            paths.append(RoutingPath(
                team_id="database",
                channels=db_team.channels,
                priority=alert_envelope.anomaly.criticality.value,
                context_scope={"database_perspective": True},
                escalation_policy=db_team.escalation_policy
            ))
        
        return self._deduplicate_paths(paths)
    
    def _deduplicate_paths(self, paths):
        """Remove duplicate paths to the same team"""
        team_paths = {}
        for path in paths:
            if path.team_id in team_paths:
                # Keep the higher priority path
                if path.priority > team_paths[path.team_id].priority:
                    team_paths[path.team_id] = path
            else:
                team_paths[path.team_id] = path
        
        return list(team_paths.values())
    
    async def _process_routing_path(self, path, original_alert, correlation_id):
        """Process a single routing path with team-specific context"""
        # Create team-scoped copy of alert
        team_alert = deepcopy(original_alert)
        
        # Add team-specific context
        team_alert.add_extension("routing_path", {
            "team_id": path.team_id,
            "correlation_id": correlation_id,
            "is_multi_team_alert": True
        })
        
        # Apply context scoping - filter or enhance information based on team needs
        self._apply_team_context(team_alert, path.context_scope)
        
        # Create a notification for each channel in this path
        notifications = []
        for channel in path.channels:
            notification = Notification(
                alert=team_alert,
                channel=channel,
                priority=path.priority,
                team_id=path.team_id,
                correlation_id=correlation_id
            )
            notifications.append(notification)
        
        return {
            "path": path,
            "team_alert": team_alert,
            "notifications": notifications
        }
    
    def _apply_team_context(self, team_alert, context_scope):
        """Apply team-specific context filtering and enrichment"""
        # Add team-relevant information
        if context_scope.get("security_perspective"):
            team_alert.add_extension("security_context", {
                "threat_level": self._calculate_threat_level(team_alert.anomaly),
                "affected_assets": self._identify_security_assets(team_alert.anomaly),
                "compliance_impact": self._assess_compliance_impact(team_alert.anomaly)
            })
            
        if context_scope.get("database_perspective"):
            team_alert.add_extension("database_context", {
                "affected_instances": self._identify_db_instances(team_alert.anomaly),
                "query_patterns": self._extract_query_patterns(team_alert.anomaly),
                "performance_metrics": self._get_related_db_metrics(team_alert.anomaly)
            })
        
        # Remove irrelevant details based on team context
        if context_scope.get("filtered_view", False):
            redacted_fields = context_scope.get("redact_fields", [])
            for field in redacted_fields:
                if field in team_alert.details:
                    team_alert.details[field] = "[REDACTED]"
    
    async def _execute_routing(self, routing_tasks, context_record):
        """Execute all routing tasks and track response status"""
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        # Process results and send notifications
        for result in results:
            if isinstance(result, Exception):
                # Handle routing errors
                continue
                
            path = result["path"]
            notifications = result["notifications"]
            
            # Register this path with the tracker
            self.path_tracker.register_path(
                context_record.correlation_id,
                path.team_id,
                path.escalation_policy
            )
            
            # Send notifications for this path
            for notification in notifications:
                try:
                    await self.send_notification(notification)
                except Exception as e:
                    # Log error but continue with other notifications
                    pass