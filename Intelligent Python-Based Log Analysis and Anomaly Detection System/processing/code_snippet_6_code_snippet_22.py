from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Set, Tuple, Optional, Any, Callable, Generator
import numpy as np
from dataclasses import dataclass
import heapq
import networkx as nx
import time
import json
import uuid

class CorrelationMethod(Enum):
    """Methods for temporal correlation analysis"""
    SEQUENTIAL = auto()  # A followed by B
    CAUSAL = auto()      # A causes B
    MUTUAL = auto()      # A and B happen together
    CYCLIC = auto()      # A and B alternate
    DEPENDENT = auto()   # B only happens when A has happened

class CorrelationType(Enum):
    """Types of identified correlations"""
    PRECURSOR = auto()       # Event that precedes others (potential root cause)
    CONSEQUENCE = auto()     # Event that follows others (impact)
    MUTUAL = auto()          # Events that co-occur
    CAUSAL_CHAIN = auto()    # Series of events with causal relationship
    PERIODIC = auto()        # Events that occur in cycles
    CONVERGING = auto()      # Multiple events leading to one
    DIVERGING = auto()       # One event leading to multiple

@dataclass
class TimeWindow:
    """Represents a time window for correlation"""
    start: datetime
    end: datetime
    
    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp is within window"""
        return self.start <= timestamp <= self.end
        
    def overlap(self, other: 'TimeWindow') -> Optional['TimeWindow']:
        """Find the overlap between two windows, if any"""
        if self.end < other.start or other.end < self.start:
            return None
            
        return TimeWindow(
            max(self.start, other.start),
            min(self.end, other.end)
        )
        
    def duration_seconds(self) -> float:
        """Get the duration of the window in seconds"""
        return (self.end - self.start).total_seconds()

@dataclass
class TemporalPattern:
    """A pattern found between temporally correlated events"""
    id: str
    pattern_type: CorrelationType
    source_clusters: List[str]  # Cluster IDs
    average_interval: Optional[float] = None  # seconds
    confidence: float = 0.0
    stability: float = 0.0  # How stable the pattern is over time
    occurrences: int = 0
    causal_confidence: float = 0.0  # Confidence in causal relationship
    discovery_time: datetime = None
    last_seen: datetime = None
    pattern_graph: Any = None  # NetworkX graph representation
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.discovery_time:
            self.discovery_time = datetime.now()
        self.last_seen = self.discovery_time
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = {
            "id": self.id,
            "pattern_type": self.pattern_type.name,
            "source_clusters": self.source_clusters,
            "confidence": self.confidence,
            "stability": self.stability,
            "occurrences": self.occurrences,
            "discovery_time": self.discovery_time.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }
        
        if self.average_interval is not None:
            result["average_interval"] = self.average_interval
            
        if self.causal_confidence > 0:
            result["causal_confidence"] = self.causal_confidence
            
        return result

class TimeSeriesStore:
    """Storage for time series data of anomalies and events"""
    
    def __init__(self, max_history_days: int = 30):
        self.series: Dict[str, List[Tuple[datetime, Any]]] = {}
        self.max_history = timedelta(days=max_history_days)
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(hours=1)
    
    def add_event(self, 
                series_id: str, 
                timestamp: datetime, 
                value: Any) -> None:
        """Add an event to a time series"""
        if series_id not in self.series:
            self.series[series_id] = []
            
        self.series[series_id].append((timestamp, value))
        
        # Occasional cleanup
        now = datetime.now()
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data()
            self.last_cleanup = now
    
    def get_window(self, 
                 series_id: str, 
                 start_time: datetime, 
                 end_time: datetime) -> List[Tuple[datetime, Any]]:
        """Get events in a time window"""
        if series_id not in self.series:
            return []
            
        return [
            (ts, value) for ts, value in self.series[series_id]
            if start_time <= ts <= end_time
        ]
    
    def get_all_series(self) -> List[str]:
        """Get all series IDs"""
        return list(self.series.keys())
    
    def get_series_stats(self, series_id: str) -> Dict:
        """Get statistics for a time series"""
        if series_id not in self.series:
            return {"count": 0}
            
        events = self.series[series_id]
        
        if not events:
            return {"count": 0}
            
        timestamps = [ts for ts, _ in events]
        
        return {
            "count": len(events),
            "first": min(timestamps),
            "last": max(timestamps),
            "duration": (max(timestamps) - min(timestamps)).total_seconds()
        }
    
    def _cleanup_old_data(self) -> int:
        """Remove data older than max_history"""
        cutoff = datetime.now() - self.max_history
        count = 0
        
        for series_id in self.series:
            original_len = len(self.series[series_id])
            self.series[series_id] = [
                (ts, value) for ts, value in self.series[series_id]
                if ts >= cutoff
            ]
            count += original_len - len(self.series[series_id])
            
        return count

class FieldTransitionTracker:
    """Tracks transitions in field values across events"""
    
    def __init__(self, max_fields: int = 100):
        self.transitions: Dict[str, Dict[Any, Dict[Any, int]]] = {}
        self.field_values: Dict[str, Set[Any]] = {}
        self.max_fields = max_fields
    
    def add_transition(self, field: str, from_value: Any, to_value: Any) -> None:
        """Record a transition in field value"""
        # Initialize dictionaries if needed
        if field not in self.transitions:
            if len(self.transitions) >= self.max_fields:
                return  # Skip if too many fields
            self.transitions[field] = {}
            self.field_values[field] = set()
            
        if from_value not in self.transitions[field]:
            self.transitions[field][from_value] = {}
            
        if to_value not in self.transitions[field][from_value]:
            self.transitions[field][from_value][to_value] = 0
            
        # Record values
        self.field_values[field].add(from_value)
        self.field_values[field].add(to_value)
            
        # Increment transition count
        self.transitions[field][from_value][to_value] += 1
    
    def get_transition_count(self, field: str, from_value: Any, to_value: Any) -> int:
        """Get the count of a specific transition"""
        if field not in self.transitions:
            return 0
            
        if from_value not in self.transitions[field]:
            return 0
            
        return self.transitions[field][from_value].get(to_value, 0)
    
    def get_next_likely_values(self, 
                             field: str, 
                             current_value: Any, 
                             min_probability: float = 0.1) -> List[Tuple[Any, float]]:
        """Get likely next values based on transition probabilities"""
        if field not in self.transitions:
            return []
            
        if current_value not in self.transitions[field]:
            return []
            
        # Calculate probabilities
        transitions = self.transitions[field][current_value]
        total = sum(transitions.values())
        
        if total == 0:
            return []
            
        probabilities = [
            (to_value, count / total) 
            for to_value, count in transitions.items()
        ]
        
        # Filter by minimum probability
        return [
            (value, prob) for value, prob in probabilities
            if prob >= min_probability
        ]
    
    def get_transition_graph(self, field: str) -> nx.DiGraph:
        """Get a directed graph of transitions for visualization"""
        G = nx.DiGraph()
        
        if field not in self.transitions:
            return G
            
        # Add nodes and edges
        for from_value, transitions in self.transitions[field].items():
            if from_value not in G:
                G.add_node(str(from_value))
                
            for to_value, count in transitions.items():
                if to_value not in G:
                    G.add_node(str(to_value))
                    
                G.add_edge(
                    str(from_value), 
                    str(to_value), 
                    weight=count, 
                    probability=count / sum(transitions.values())
                )
                
        return G
    
    def get_field_stats(self, field: str) -> Dict:
        """Get statistics for a field's transitions"""
        if field not in self.transitions:
            return {"transitions": 0}
            
        total_transitions = sum(
            sum(transitions.values())
            for transitions in self.transitions[field].values()
        )
        
        values = len(self.field_values.get(field, set()))
        
        # Find most common transition
        most_common = (None, None, 0)
        for from_value, transitions in self.transitions[field].items():
            for to_value, count in transitions.items():
                if count > most_common[2]:
                    most_common = (from_value, to_value, count)
                    
        return {
            "transitions": total_transitions,
            "unique_values": values,
            "most_common": {
                "from": most_common[0],
                "to": most_common[1],
                "count": most_common[2]
            } if most_common[2] > 0 else None
        }

class SlidingWindowCounter:
    """Efficient counter for events in sliding time windows"""
    
    def __init__(self, window_seconds: int = 3600):
        self.window_size = window_seconds
        self.events = deque()  # (timestamp, identifier)
        self.counts = defaultdict(int)
    
    def add(self, identifier: str) -> None:
        """Add an event occurrence"""
        timestamp = time.time()
        self.events.append((timestamp, identifier))
        self.counts[identifier] += 1
        
        # Remove old events
        self._cleanup()
    
    def _cleanup(self) -> None:
        """Remove events outside the sliding window"""
        cutoff = time.time() - self.window_size
        
        while self.events and self.events[0][0] < cutoff:
            _, identifier = self.events.popleft()
            self.counts[identifier] -= 1
            
            if self.counts[identifier] <= 0:
                del self.counts[identifier]
    
    def get_count(self, identifier: str) -> int:
        """Get count of an identifier within window"""
        self._cleanup()
        return self.counts.get(identifier, 0)
    
    def get_all_counts(self) -> Dict[str, int]:
        """Get counts of all identifiers within window"""
        self._cleanup()
        return dict(self.counts)

class InterEventIntervalTracker:
    """Tracks intervals between related events"""
    
    def __init__(self, max_history: int = 1000):
        self.intervals: Dict[Tuple[str, str], List[float]] = {}
        self.max_history = max_history
    
    def add_interval(self, from_event: str, to_event: str, interval_seconds: float) -> None:
        """Record an interval between events"""
        key = (from_event, to_event)
        
        if key not in self.intervals:
            self.intervals[key] = []
            
        self.intervals[key].append(interval_seconds)
        
        # Prune if needed
        if len(self.intervals[key]) > self.max_history:
            self.intervals[key] = self.intervals[key][-self.max_history:]
    
    def get_average_interval(self, from_event: str, to_event: str) -> Optional[float]:
        """Get average interval between events"""
        key = (from_event, to_event)
        
        if key not in self.intervals or not self.intervals[key]:
            return None
            
        return sum(self.intervals[key]) / len(self.intervals[key])
    
    def get_interval_stats(self, from_event: str, to_event: str) -> Dict:
        """Get statistics about intervals"""
        key = (from_event, to_event)
        
        if key not in self.intervals or not self.intervals[key]:
            return {"count": 0}
            
        intervals = self.intervals[key]
        
        return {
            "count": len(intervals),
            "min": min(intervals),
            "max": max(intervals),
            "avg": sum(intervals) / len(intervals),
            "median": sorted(intervals)[len(intervals) // 2],
            "std_dev": np.std(intervals)
        }
    
    def is_periodic(self, 
                  from_event: str, 
                  to_event: str, 
                  max_variance_ratio: float = 0.2) -> bool:
        """Check if intervals between events are periodic"""
        stats = self.get_interval_stats(from_event, to_event)
        
        if stats.get("count", 0) < 3:
            return False
            
        # Check if standard deviation is relatively small
        std_dev_ratio = stats.get("std_dev", float('inf')) / stats.get("avg", 1)
        
        return std_dev_ratio <= max_variance_ratio

class EventSequenceDetector:
    """Detects common sequences of events"""
    
    def __init__(self, max_sequence_length: int = 5):
        self.max_length = max_sequence_length
        self.sequences: Dict[Tuple[str, ...], int] = {}
    
    def add_sequence(self, events: List[str]) -> None:
        """Add a sequence of events"""
        # Generate subsequences up to max_length
        n = len(events)
        
        for length in range(2, min(n+1, self.max_length+1)):
            for i in range(n - length + 1):
                subsequence = tuple(events[i:i+length])
                
                if subsequence not in self.sequences:
                    self.sequences[subsequence] = 0
                    
                self.sequences[subsequence] += 1
    
    def get_common_sequences(self, min_count: int = 2) -> List[Tuple[Tuple[str, ...], int]]:
        """Get common sequences by frequency"""
        return [
            (seq, count) for seq, count in self.sequences.items()
            if count >= min_count
        ]
    
    def get_top_sequences(self, top_n: int = 10) -> List[Tuple[Tuple[str, ...], int]]:
        """Get top-n most common sequences"""
        return sorted(
            self.sequences.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

class TemporalCorrelator:
    """Detects temporal correlations between anomaly clusters"""
    
    def __init__(
        self,
        cluster_manager,
        min_confidence: float = 0.6,
        min_occurrences: int = 3,
        default_lookback_window: int = 3600,  # seconds
        causal_threshold: float = 0,7,
        max_patterns: int = 1000
    ):
        self.cluster_manager = cluster_manager
        self.min_confidence = min_confidence
        self.min_occurrences = min_occurrences
        self.default_lookback_window = default_lookback_window
        self.causal_threshold = causal_threshold
        self.max_patterns = max_patterns
        
        # Storage components
        self.time_series = TimeSeriesStore()
        self.field_transitions = FieldTransitionTracker()
        self.interval_tracker = InterEventIntervalTracker()
        self.sequence_detector = EventSequenceDetector()
        self.window_counter = SlidingWindowCounter()
        
        # Pattern storage
        self.patterns: Dict[str, TemporalPattern] = {}
        self.pattern_graph = nx.DiGraph()  # For causality analysis
        
        # Service topology for context
        self.service_graph = nx.DiGraph()
        
        # Active windows being monitored
        self.active_windows: Dict[str, TimeWindow] = {}
    
    def process_anomaly(self, anomaly: Anomaly) -> Dict:
        """Process an anomaly for temporal correlation"""
        fingerprint = anomaly.fingerprint
        service = anomaly.service_name
        timestamp = anomaly.timestamp
        
        # Get cluster for this anomaly if available
        cluster = self.cluster_manager.get_cluster_for_fingerprint(fingerprint)
        if not cluster:
            return {"status": "not_clustered"}
            
        cluster_id = cluster.cluster_id
        
        # Add to time series store
        self.time_series.add_event(
            f"cluster:{cluster_id}", 
            timestamp,
            {
                "fingerprint": fingerprint,
                "service": service,
                "anomaly_type": anomaly.anomaly_type.name,
                "details": anomaly.details
            }
        )
        
        # Also track by service
        self.time_series.add_event(
            f"service:{service}",
            timestamp,
            {
                "fingerprint": fingerprint,
                "cluster_id": cluster_id,
                "anomaly_type": anomaly.anomaly_type.name,
                "details": anomaly.details
            }
        )
        
        # Record in window counter
        self.window_counter.add(f"cluster:{cluster_id}")
        self.window_counter.add(f"service:{service}")
        
        # Track field transitions
        self._track_field_transitions(anomaly, cluster_id)
        
        # Look for sequences in active windows
        correlations = self._check_temporal_correlations(
            anomaly, cluster_id, timestamp)
            
        # Find potential patterns
        new_patterns = self._detect_patterns(
            anomaly, cluster_id, correlations)
            
        return {
            "cluster_id": cluster_id,
            "correlations": correlations,
            "patterns": [p.to_dict() for p in new_patterns]
        }
    
    def _track_field_transitions(self, anomaly: Anomaly, cluster_id: str) -> None:
        """Track transitions in key fields"""
        # Extract fields we care about from anomaly details
        details = anomaly.details
        
        # Track transitions in status fields if present
        for field in ["status", "state", "health", "condition"]:
            if field in details and isinstance(details[field], (str, int, bool)):
                # Find previous value for this cluster and field
                lookback = datetime.now() - timedelta(seconds=self.default_lookback_window)
                events = self.time_series.get_window(
                    f"cluster:{cluster_id}", lookback, datetime.now())
                
                # Sort by timestamp descending
                events.sort(key=lambda x: x[0], reverse=True)
                
                prev_value = None
                for _, event_data in events[1:]:  # Skip current event
                    if field in event_data.get("details", {}):
                        prev_value = event_data["details"][field]
                        break
                
                if prev_value is not None and prev_value != details[field]:
                    # Record transition
                    self.field_transitions.add_transition(
                        field, prev_value, details[field]
                    )
    
    def _check_temporal_correlations(
        self, 
        anomaly: Anomaly, 
        cluster_id: str, 
        timestamp: datetime
    ) -> List[Dict]:
        """Check for temporal correlations with other clusters"""
        correlations = []
        
        # Define lookback window
        lookback = timestamp - timedelta(seconds=self.default_lookback_window)
        
        # Get all active clusters
        active_clusters = [
            c for c in self.cluster_manager.clusters.values()
            if c.is_active and c.cluster_id != cluster_id
        ]
        
        for other_cluster in active_clusters:
            other_id = other_cluster.cluster_id
            
            # Get events for other cluster in lookback window
            other_events = self.time_series.get_window(
                f"cluster:{other_id}", lookback, timestamp
            )
            
            if not other_events:
                continue
                
            # Calculate timing relationship
            other_events.sort(key=lambda x: x[0])
            latest_other_time = other_events[-1][0]
            time_delta = (timestamp - latest_other_time).total_seconds()
            
            # Record interval
            self.interval_tracker.add_interval(
                other_id, cluster_id, time_delta
            )
            
            # Different correlation types based on timing and frequency
            other_count = len(other_events)
            is_frequent = other_count >= 3
            
            # Check if clusters involve services with known relationships
            services_related = self._are_services_related(
                anomaly.service_name,
                other_events[-1][1].get("service")
            )
            
            correlation = {
                "source_cluster": other_id,
                "target_cluster": cluster_id,
                "time_delta_seconds": time_delta,
                "source_events_count": other_count,
                "services_related": services_related
            }
            
            # Determine correlation type
            if 0 < time_delta < 30 and is_frequent:
                # Very close in time - likely sequence
                correlation["correlation_type"] = "SEQUENTIAL"
                correlation["confidence"] = 0.8 if services_related else 0.6
            elif 30 <= time_delta < 300 and services_related:
                # Service-related with reasonable gap - possible causation
                correlation["correlation_type"] = "CAUSAL"
                correlation["confidence"] = 0.7
            elif abs(time_delta) < 10:
                # Nearly simultaneous - mutual
                correlation["correlation_type"] = "MUTUAL"
                correlation["confidence"] = 0.9 if services_related else 0.7
            else:
                # Default - possible correlation
                correlation["correlation_type"] = "POTENTIAL"
                correlation["confidence"] = 0.5 if services_related else 0.3
                
            correlations.append(correlation)
            
            # Also track event sequences for pattern detection
            if len(correlations) > 0:
                sequence = [
                    ev[1].get("fingerprint") for ev in other_events
                ]
                sequence.append(anomaly.fingerprint)
                self.sequence_detector.add_sequence(sequence)
                
        return correlations
    
    def _are_services_related(self, service1: str, service2: str) -> bool:
        """Check if services are related in the service topology"""
        if not service1 or not service2 or service1 == service2:
            return False
            
        # If we have a service graph, use it
        if service1 in self.service_graph and service2 in self.service_graph:
            # Check if connected directly
            if service2 in self.service_graph[service1] or service1 in self.service_graph[service2]:
                return True
                
            # Check if connected by one hop
            for neighbor in self.service_graph[service1]:
                if service2 in self.service_graph[neighbor]:
                    return True
                    
        return False
    
    def _detect_patterns(
        self, 
        anomaly: Anomaly, 
        cluster_id: str,
        correlations: List[Dict]
    ) -> List[TemporalPattern]:
        """Detect temporal patterns based on correlations"""
        new_patterns = []
        
        # Group correlations by type
        by_type = {}
        for corr in correlations:
            corr_type = corr["correlation_type"]
            if corr_type not in by_type:
                by_type[corr_type] = []
            by_type[corr_type].append(corr)
            
        # Look for precursor patterns
        if "CAUSAL" in by_type:
            causal_correlations = by_type["CAUSAL"]
            
            # Group by source cluster
            by_source = {}
            for corr in causal_correlations:
                source = corr["source_cluster"]
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(corr)
                
            # Check if any source appears consistently before this cluster
            for source, source_correlations in by_source.items():
                if len(source_correlations) >= self.min_occurrences:
                    # Check interval consistency
                    intervals = [
                        corr["time_delta_seconds"] for corr in source_correlations
                    ]
                    avg_interval = sum(intervals) / len(intervals)
                    std_dev = np.std(intervals)
                    
                    # Stable intervals indicate a pattern
                    if std_dev / avg_interval < 0.3:  # Relatively stable
                        pattern = TemporalPattern(
                            id=None,
                            pattern_type=CorrelationType.PRECURSOR,
                            source_clusters=[source, cluster_id],
                            average_interval=avg_interval,
                            confidence=0.7,
                            stability=1.0 - (std_dev / avg_interval),
                            occurrences=len(source_correlations),
                            causal_confidence=0.6
                        )
                        new_patterns.append(pattern)
                        self.patterns[pattern.id] = pattern
        
        # Look for mutual occurrence patterns
        if "MUTUAL" in by_type:
            mutual_correlations = by_type["MUTUAL"]
            
            # Group by time range
            time_clustered = self._time_cluster_correlations(mutual_correlations, 10)
            
            # If we have multiple clusters happening together consistently
            if any(len(group) >= 3 for group in time_clustered):
                for group in time_clustered:
                    if len(group) >= 3:
                        source_clusters = [corr["source_cluster"] for corr in group]
                        source_clusters.append(cluster_id)
                        
                        pattern = TemporalPattern(
                            id=None,
                            pattern_type=CorrelationType.MUTUAL,
                            source_clusters=source_clusters,
                            confidence=0.8,
                            stability=0.7,
                            occurrences=len(group),
                            causal_confidence=0.3
                        )
                        new_patterns.append(pattern)
                        self.patterns[pattern.id] = pattern
        
        # Look for sequential patterns using detected sequences
        common_sequences = self.sequence_detector.get_common_sequences(
            min_count=self.min_occurrences
        )
        
        for sequence, count in common_sequences:
            if len(sequence) >= 3 and sequence[-1] == anomaly.fingerprint:
                # Get clusters for these fingerprints
                fp_to_cluster = {}
                for fp in sequence:
                    cluster = self.cluster_manager.get_cluster_for_fingerprint(fp)
                    if cluster:
                        fp_to_cluster[fp] = cluster.cluster_id
                
                if len(fp_to_cluster) == len(sequence):
                    # We have a valid cluster sequence
                    cluster_sequence = [fp_to_cluster[fp] for fp in sequence]
                    
                    pattern = TemporalPattern(
                        id=None,
                        pattern_type=CorrelationType.CAUSAL_CHAIN,
                        source_clusters=cluster_sequence,
                        confidence=0.6,
                        stability=0.6,
                        occurrences=count,
                        causal_confidence=0.5
                    )
                    new_patterns.append(pattern)
                    self.patterns[pattern.id] = pattern
                    
        # If we're generating too many patterns, prune older ones
        self._prune_patterns()
                    
        return new_patterns
    
    def _time_cluster_correlations(
        self, 
        correlations: List[Dict],
        max_seconds: float
    ) -> List[List[Dict]]:
        """Group correlations that happen within a short time of each other"""
        if not correlations:
            return []
            
        # Sort by time delta
        sorted_correlations = sorted(
            correlations,
            key=lambda x: x["time_delta_seconds"]
        )
        
        groups = []
        current_group = [sorted_correlations[0]]
        
        for corr in sorted_correlations[1:]:
            last_delta = current_group[-1]["time_delta_seconds"]
            curr_delta = corr["time_delta_seconds"]
            
            if abs(curr_delta - last_delta) <= max_seconds:
                current_group.append(corr)
            else:
                groups.append(current_group)
                current_group = [corr]
                
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def _prune_patterns(self) -> int:
        """Prune patterns to stay under max_patterns limit"""
        if len(self.patterns) <= self.max_patterns:
            return 0
            
        # Calculate how many to remove
        to_remove = len(self.patterns) - self.max_patterns
        
        # Sort by confidence * stability * occurrences (lower is worse)
        pattern_scores = [
            (
                pattern.id,
                pattern.confidence * pattern.stability * pattern.occurrences
            )
            for pattern in self.patterns.values()
        ]
        
        pattern_scores.sort(key=lambda x: x[1])
        
        # Remove lowest scoring patterns
        for i in range(to_remove):
            if i < len(pattern_scores):
                pattern_id = pattern_scores[i][0]
                if pattern_id in self.patterns:
                    del self.patterns[pattern_id]
                    
        return to_remove
    
    def get_related_patterns(self, cluster_id: str) -> List[TemporalPattern]:
        """Get patterns related to a specific cluster"""
        return [
            pattern for pattern in self.patterns.values()
            if cluster_id in pattern.source_clusters
        ]
    
    def get_causal_graph(self, max_patterns: int = 100) -> nx.DiGraph:
        """Build a causal graph of clusters based on detected patterns"""
        G = nx.DiGraph()
        
        # Start with top patterns by confidence
        top_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.confidence * p.causal_confidence,
            reverse=True
        )[:max_patterns]
        
        # Add nodes and edges
        for pattern in top_patterns:
            if pattern.pattern_type in [CorrelationType.PRECURSOR, CorrelationType.CAUSAL_CHAIN]:
                clusters = pattern.source_clusters
                
                # Add all clusters as nodes
                for cluster in clusters:
                    if cluster not in G:
                        G.add_node(cluster)
                
                # Add causal edges
                if pattern.pattern_type == CorrelationType.PRECURSOR and len(clusters) >= 2:
                    G.add_edge(
                        clusters[0], 
                        clusters[1], 
                        confidence=pattern.causal_confidence,
                        pattern_id=pattern.id,
                        interval=pattern.average_interval
                    )
                elif pattern.pattern_type == CorrelationType.CAUSAL_CHAIN:
                    for i in range(len(clusters) - 1):
                        G.add_edge(
                            clusters[i],
                            clusters[i+1],
                            confidence=pattern.causal_confidence / len(clusters),
                            pattern_id=pattern.id,
                            chain_position=i
                        )
        
        return G
    
    def get_root_cause_candidates(self, cluster_id: str) -> List[Dict]:
        """Find potential root causes for a cluster based on causal graph"""
        causal_graph = self.get_causal_graph()
        
        if cluster_id not in causal_graph:
            return []
            
        # Find all predecessors (potential causes)
        predecessors = list(causal_graph.predecessors(cluster_id))
        if not predecessors:
            return []
            
        # For each precursor, calculate confidence and distance
        candidates = []
        
        for pred in predecessors:
            edge_data = causal_graph.get_edge_data(pred, cluster_id)
            confidence = edge_data.get("confidence", 0)
            
            # Get additional info about this cluster
            cluster = self.cluster_manager.get_cluster(pred)
            
            candidates.append({
                "cluster_id": pred,
                "confidence": confidence,
                "services": list(cluster.services) if cluster else [],
                "pattern_id": edge_data.get("pattern_id"),
                "causal_distance": 1
            })
            
        # Also try to find second-level causes
        for pred in predecessors:
            pred_preds = list(causal_graph.predecessors(pred))
            for pred_pred in pred_preds:
                edge1 = causal_graph.get_edge_data(pred_pred, pred)
                edge2 = causal_graph.get_edge_data(pred, cluster_id)
                
                # Confidence decreases with distance
                combined_confidence = edge1.get("confidence", 0) * edge2.get("confidence", 0)
                
                # Get cluster info
                cluster = self.cluster_manager.get_cluster(pred_pred)
                
                candidates.append({
                    "cluster_id": pred_pred,
                    "confidence": combined_confidence,
                    "services": list(cluster.services) if cluster else [],
                    "causal_distance": 2,
                    "intermediate_cluster": pred,
                    "pattern_ids": [edge1.get("pattern_id"), edge2.get("pattern_id")]
                })
        
        # Sort by confidence
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        
        return candidates
    
    def register_service_dependency(
        self, 
        from_service: str, 
        to_service: str,
        dependency_type: str = "calls"
    ) -> None:
        """Register a dependency between services in the topology"""
        if from_service not in self.service_graph:
            self.service_graph.add_node(from_service)
            
        if to_service not in self.service_graph:
            self.service_graph.add_node(to_service)
            
        self.service_graph.add_edge(
            from_service, 
            to_service, 
            type=dependency_type
        )
    
    def analyze_communication_paths(self, 
                                 source_cluster: str,
                                 target_cluster: str) -> List[Dict]:
        """Analyze possible communication paths between clusters"""
        # Get services involved in each cluster
        source_cluster_obj = self.cluster_manager.get_cluster(source_cluster)
        target_cluster_obj = self.cluster_manager.get_cluster(target_cluster)
        
        if not source_cluster_obj or not target_cluster_obj:
            return []
            
        source_services = source_cluster_obj.services
        target_services = target_cluster_obj.services
        
        # Find all paths between services
        paths = []
        
        for s_service in source_services:
            for t_service in target_services:
                if s_service in self.service_graph and t_service in self.service_graph:
                    try:
                        # Find all simple paths
                        service_paths = list(nx.all_simple_paths(
                            self.service_graph, 
                            s_service, 
                            t_service,
                            cutoff=3  # Limit path length
                        ))
                        
                        for path in service_paths:
                            path_info = {
                                "source_service": s_service,
                                "target_service": t_service,
                                "path": path,
                                "length": len(path) - 1,  # Number of edges
                            }
                            paths.append(path_info)
                    except nx.NetworkXNoPath:
                        continue
        
        # Sort by path length
        paths.sort(key=lambda x: x["length"])
        
        return paths
    
    def get_aligned_time_windows(
        self, 
        patterns: List[TemporalPattern],
        window_size_seconds: int = 600
    ) -> Dict[str, List[TimeWindow]]:
        """Get aligned time windows across patterns for analysis"""
        if not patterns:
            return {}
            
        # Extract all clusters involved
        all_clusters = set()
        for pattern in patterns:
            all_clusters.update(pattern.source_clusters)
            
        result = {}
        
        # For each cluster, find meaningful time windows
        for cluster_id in all_clusters:
            # Get time series data
            series = self.time_series.get_series_stats(f"cluster:{cluster_id}")
            
            if series.get("count", 0) <= 1:
                continue
                
            # Create windows around activity spikes
            windows = []
            events = self.time_series.get_window(
                f"cluster:{cluster_id}",
                series["first"] - timedelta(seconds=10),
                series["last"] + timedelta(seconds=10)
            )
            
            # Sort by timestamp
            events.sort(key=lambda x: x[0])
            
            # Find areas of activity
            i = 0
            while i < len(events):
                window_start = events[i][0]
                window_end = window_start + timedelta(seconds=window_size_seconds)
                
                # Extend window to include nearby events
                while i < len(events) and events[i][0] <= window_end:
                    window_end = events[i][0] + timedelta(seconds=window_size_seconds/2)
                    i += 1
                
                windows.append(TimeWindow(window_start, window_end))
                
                # Find next window start (skip to events outside current window)
                while i < len(events) and events[i][0] <= window_end:
                    i += 1
            
            if windows:
                result[cluster_id] = windows
        
        return result
    
    def find_aligned_windows(
        self, 
        window_map: Dict[str, List[TimeWindow]],
        min_overlap_seconds: int = 30
    ) -> List[Dict]:
        """Find time windows that align across multiple clusters"""
        if not window_map:
            return []
            
        # Generate all possible window combinations
        clusters = list(window_map.keys())
        alignments = []
        
        # For each window of the first cluster
        for window1 in window_map[clusters[0]]:
            aligned_windows = {clusters[0]: window1}
            
            # Try to find overlapping windows from other clusters
            for cluster in clusters[1:]:
                best_overlap = None
                best_window = None
                
                for window2 in window_map[cluster]:
                    overlap = window1.overlap(window2)
                    if overlap:
                        overlap_duration = overlap.duration_seconds()
                        if overlap_duration >= min_overlap_seconds:
                            if best_overlap is None or overlap_duration > best_overlap:
                                best_overlap = overlap_duration
                                best_window = window2
                
                if best_window:
                    aligned_windows[cluster] = best_window
            
            # If we have at least 2 aligned windows, record it
            if len(aligned_windows) >= 2:
                # Calculate common overlap across all windows
                common_overlap = self._find_common_overlap([w for w in aligned_windows.values()])
                
                if common_overlap and common_overlap.duration_seconds() >= min_overlap_seconds:
                    alignments.append({
                        "clusters": list(aligned_windows.keys()),
                        "windows": {
                            cluster: {
                                "start": window.start.isoformat(),
                                "end": window.end.isoformat(),
                                "duration": window.duration_seconds()
                            }
                            for cluster, window in aligned_windows.items()
                        },
                        "common_overlap": {
                            "start": common_overlap.start.isoformat(),
                            "end": common_overlap.end.isoformat(),
                            "duration": common_overlap.duration_seconds()
                        },
                        "cluster_count": len(aligned_windows)
                    })
        
        # Sort by number of clusters involved (descending)
        alignments.sort(key=lambda x: x["cluster_count"], reverse=True)
        
        return alignments
    
    def _find_common_overlap(self, windows: List[TimeWindow]) -> Optional[TimeWindow]:
        """Find the common overlap period across multiple time windows"""
        if not windows:
            return None
            
        result = windows[0]
        
        for window in windows[1:]:
            result = result.overlap(window)
            if not result:
                return None
                
        return result
    
    def analyze_causal_field_transitions(
        self,
        source_cluster: str,
        target_cluster: str,
        time_window: Optional[TimeWindow] = None
    ) -> List[Dict]:
        """Analyze field transitions between causally related clusters"""
        # Define time window if not provided
        if not time_window:
            # Get latest events for both clusters
            source_stats = self.time_series.get_series_stats(f"cluster:{source_cluster}")
            target_stats = self.time_series.get_series_stats(f"cluster:{target_cluster}")
            
            if "last" not in source_stats or "last" not in target_stats:
                return []
                
            # Create window spanning both clusters with buffer
            window_start = min(source_stats["first"], target_stats["first"])
            window_start -= timedelta(seconds=60)  # 1 minute buffer
            
            window_end = max(source_stats["last"], target_stats["last"])
            window_end += timedelta(seconds=60)  # 1 minute buffer
            
            time_window = TimeWindow(window_start, window_end)
        
        # Get events in window
        source_events = self.time_series.get_window(
            f"cluster:{source_cluster}",
            time_window.start,
            time_window.end
        )
        
        target_events = self.time_series.get_window(
            f"cluster:{target_cluster}",
            time_window.start,
            time_window.end
        )
        
        # Sort by timestamp
        source_events.sort(key=lambda x: x[0])
        target_events.sort(key=lambda x: x[0])
        
        # Extract field values over time
        source_fields = self._extract_field_timeline(source_events)
        target_fields = self._extract_field_timeline(target_events)
        
        # Look for potential causal transitions
        causal_transitions = []
        
        for field in source_fields:
            if field not in target_fields:
                continue
                
            source_timeline = source_fields[field]
            target_timeline = target_fields[field]
            
            # Look for value changes in source followed by changes in target
            for i in range(len(source_timeline) - 1):
                s_time, s_old_value = source_timeline[i]
                s_next_time, s_new_value = source_timeline[i + 1]
                
                # Only interested in changes
                if s_old_value == s_new_value:
                    continue
                    
                # Look for changes in target after this source change
                for j in range(len(target_timeline) - 1):
                    t_time, t_old_value = target_timeline[j]
                    t_next_time, t_new_value = target_timeline[j + 1]
                    
                    # Skip if target change is before source change
                    if t_next_time <= s_next_time:
                        continue
                        
                    # Skip if no change
                    if t_old_value == t_new_value:
                        continue
                    
                    # Calculate delay
                    delay_seconds = (t_next_time - s_next_time).total_seconds()
                    
                    # If change happens within reasonable time
                    if delay_seconds <= 300:  # 5 minute window
                        transition = {
                            "field": field,
                            "source_change": {
                                "from": s_old_value,
                                "to": s_new_value,
                                "at": s_next_time.isoformat()
                            },
                            "target_change": {
                                "from": t_old_value,
                                "to": t_new_value,
                                "at": t_next_time.isoformat()
                            },
                            "delay_seconds": delay_seconds,
                            "confidence": 0.6,  # Base confidence
                        }
                        
                        # Higher confidence for known field transitions
                        transition_count = self.field_transitions.get_transition_count(
                            field, s_new_value, t_new_value)
                            
                        if transition_count > 0:
                            transition["confidence"] = min(0.9, 0.6 + (transition_count * 0.05))
                            transition["observed_count"] = transition_count
                            
                        causal_transitions.append(transition)
        
        # Sort by confidence
        causal_transitions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return causal_transitions
    
    def _extract_field_timeline(
        self, 
        events: List[Tuple[datetime, Any]]
    ) -> Dict[str, List[Tuple[datetime, Any]]]:
        """Extract timeline of field values from events"""
        result = {}
        
        for timestamp, event_data in events:
            details = event_data.get("details", {})
            
            # Track fields we're interested in
            for field in ["status", "state", "health", "condition", "error_code", "level"]:
                if field in details:
                    if field not in result:
                        result[field] = []
                        
                    result[field].append((timestamp, details[field]))
        
        return result