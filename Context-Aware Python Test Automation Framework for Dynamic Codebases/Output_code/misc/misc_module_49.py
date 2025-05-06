class DynamicTaskScheduler(TaskScheduler):
    """
    Dynamically schedules tasks based on estimated complexity
    and worker capacity
    """
    def schedule_tasks(self, conflict_regions, context):
        tasks = []
        
        # Sort regions by complexity (most complex first for better load balancing)
        sorted_regions = sorted(
            conflict_regions, 
            key=lambda r: r.get_complexity_score(),
            reverse=True
        )
        
        for region in sorted_regions:
            # Determine evaluation type based on complexity and context
            evaluation_type = self._select_evaluation_type(region, context)
            
            # Create the task
            task = {
                "region_id": region.id,
                "proposals": region.proposals,
                "context": self._prepare_context(context, region),
                "evaluation_type": evaluation_type,
                "priority": self._calculate_priority(region, context)
            }
            
            tasks.append(task)
            
        return tasks
        
    def _select_evaluation_type(self, region, context):
        """Select the appropriate evaluation type based on region properties"""
        complexity = region.get_complexity_score()
        
        # If high urgency, use fast evaluation
        if context.get("urgency", 0) > 0.8:
            return "fast"
            
        # If incremental evaluation is possible, use it
        if self._can_use_incremental(region, context):
            return "incremental"
            
        # For very complex regions, use fast evaluation
        if complexity > 1000:  # Arbitrary threshold
            return "fast"
            
        # Default to full evaluation
        return "full"
        
    def _can_use_incremental(self, region, context):
        """Check if incremental evaluation is possible"""
        # Would check if we have relevant previous state and
        # if the changes are amenable to incremental evaluation
        return False  # Placeholder
        
    def _prepare_context(self, global_context, region):
        """Prepare a context specific to this region"""
        if not global_context:
            return {"region_id": region.id}
            
        # Clone to avoid modifying the original
        context = global_context.copy()
        
        # Add region-specific information
        context["region_id"] = region.id
        context["region_bounds"] = (region.bounding_box.start, region.bounding_box.end)
        
        return context
        
    def _calculate_priority(self, region, context):
        """Calculate task priority for scheduling"""
        # Base priority on complexity and other factors
        priority = region.get_complexity_score() / 100.0
        
        # Adjust based on urgency
        urgency = context.get("urgency", 0.5)
        priority *= (1 + urgency)
        
        # Adjust for important agents
        agent_boost = 0
        for agent_id in region.interested_agents:
            importance = context.get("agent_importance", {}).get(agent_id, 0.5)
            agent_boost = max(agent_boost, importance)
            
        priority *= (1 + agent_boost)
        
        return min(10, priority)  # Cap at 10