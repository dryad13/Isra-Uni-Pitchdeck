"""M07 — watchdog event handler bridging filesystem events to the controller."""

from __future__ import annotations

from watchdog.events import FileSystemEventHandler


class DropzoneEventHandler(FileSystemEventHandler):
    def __init__(self, controller) -> None:
        self._controller = controller

    def _dispatch(self, path: str) -> None:
        self._controller.ingest_path(path)

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._dispatch(event.src_path)

    def on_moved(self, event) -> None:
        if not event.is_directory:
            self._dispatch(event.dest_path)

    def on_modified(self, event) -> None:
        # Windows often finishes large copies with modified events only.
        if not event.is_directory:
            self._dispatch(event.src_path)
