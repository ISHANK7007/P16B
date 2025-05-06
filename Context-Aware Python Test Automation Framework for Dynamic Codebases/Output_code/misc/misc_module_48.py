class TaskScheduler(ABC):
    """
    Base class for task scheduling strategies
    """
    @abstractmethod
    def schedule_tasks(self, conflict_regions, context):
        """
        Schedule tasks for processing conflict regions
        Returns a list of task descriptors
        """
        pass