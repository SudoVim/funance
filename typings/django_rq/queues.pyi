import datetime
from typing import Any, Callable

class Scheduler:
    def enqueue_at(
        self, dt: datetime.datetime, job: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any: ...

def get_scheduler(queue: str) -> Scheduler: ...
