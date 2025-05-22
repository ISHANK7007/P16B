class AuditableNotificationService:
    """Notification service with complete delivery tracking"""
    
    def __init__(self, escalation_ledger):
        self.ledger = escalation_ledger
        self.notification_providers = {}  # Channel type to provider mapping
        self.delivery_tracker = DeliveryTracker()
        
    async def send_notification(self, notification):
        """Send notification with delivery tracking and ledger recording"""
        # Generate tracking ID
        delivery_id = str(uuid.uuid4())
        
        # Record notification attempt
        event = await self.ledger.record_event(
            alert_id=notification.alert.id,
            event_type=EventType.TEAM_NOTIFICATION,
            data={
                "delivery_id": delivery_id,
                "team_id": notification.team_id,
                "channel": notification.channel,
                "priority": notification.priority,
                "notification_type": notification.type
            },
            metadata={
                "correlation_id": notification.alert.extensions.get("correlation_id"),
                "attempt_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Track delivery attempt
        self.delivery_tracker.start_delivery(delivery_id, notification)
        
        try:
            # Get appropriate provider for this channel
            provider = self._get_provider(notification.channel)
            
            # Send notification
            result = await provider.send(notification)
            
            # Update delivery status in tracker
            self.delivery_tracker.complete_delivery(
                delivery_id, 
                "delivered", 
                result
            )
            
            # Record delivery success
            await self.ledger.record_event(
                alert_id=notification.alert.id,
                event_type=EventType.TEAM_NOTIFICATION,
                data={
                    "delivery_id": delivery_id,
                    "status": "delivered",
                    "provider_response": result,
                    "delivery_timestamp": datetime.utcnow().isoformat()
                },
                metadata={
                    "correlation_id": notification.alert.extensions.get("correlation_id"),
                    "event_sequence_id": event.sequence_id
                }
            )
            
            return result
        except Exception as e:
            # Update delivery status in tracker
            self.delivery_tracker.complete_delivery(
                delivery_id, 
                "failed", 
                str(e)
            )
            
            # Record delivery failure
            await self.ledger.record_event(
                alert_id=notification.alert.id,
                event_type=EventType.TEAM_NOTIFICATION,
                data={
                    "delivery_id": delivery_id,
                    "status": "failed",
                    "error": str(e),
                    "failure_timestamp": datetime.utcnow().isoformat()
                },
                metadata={
                    "correlation_id": notification.alert.extensions.get("correlation_id"),
                    "event_sequence_id": event.sequence_id
                }
            )
            
            # Re-raise for caller handling
            raise NotificationDeliveryError(f"Failed to deliver notification: {str(e)}")