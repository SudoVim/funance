from typing import Any

from django_rq.management.commands.rqscheduler import Command as RQCommand
from typing_extensions import override


class Command(RQCommand):
    @override
    def handle(self, *args: Any, **kwargs: Any):
        import funance.schedules  # pyright: ignore[reportUnusedImport]

        return super(Command, self).handle(*args, **kwargs)
