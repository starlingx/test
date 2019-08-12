"""Watch for events on files

This module watch for events in a specific path and print the last line in
console.
"""

from __future__ import print_function

import os
import sys
import time

from bash import bash
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class CustomHandler(PatternMatchingEventHandler):
    """Watch for events on files"""

    patterns = ['*console.txt']

    @staticmethod
    def process(event):
        """Process the event type

        :param event: this param has the following attributes
            event.event_type
                'modified' | 'created' | 'moved' | 'deleted'
            event.is_directory
                True | False
            event.src_path
                path/to/observed/file
        """
        # the file will be processed there
        # print event.src_path, event.event_type  # print now only for debug
        last_line = bash('tail -2 {}'.format(event.src_path))

        if 'LAST_CONSOLE_LINE' not in os.environ:
            os.environ['LAST_CONSOLE_LINE'] = last_line.stdout
            print('{}'.format(last_line.stdout))

        elif os.environ.get('LAST_CONSOLE_LINE') != last_line.stdout:
            os.environ['LAST_CONSOLE_LINE'] = last_line.stdout
            print('{}'.format(last_line.stdout))

    def on_modified(self, event):
        """Handle on modified events

        If the file(s) matches with the patterns variable declared in this
        class are modified, this function will call to process call function.
        """
        self.process(event)

    def on_created(self, event):
        """Handle on created events

        If the file(s) matches with the patterns variable declared in this
        class are created, this function will call to process call function.
        """
        self.process(event)


if __name__ == '__main__':
    ARGS = sys.argv[1:]
    OBSERVER = Observer()
    OBSERVER.schedule(CustomHandler(), path=ARGS[0] if ARGS else '.')
    OBSERVER.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        OBSERVER.stop()

    OBSERVER.join()
