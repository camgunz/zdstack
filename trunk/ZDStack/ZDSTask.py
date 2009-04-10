import logging

from threading import Event

class Task(object):

    def __init__(self, func, args=None, kwargs=None, name=None):
        self.func = func
        self.args = args or list()
        self.kwargs = kwargs or dict()
        self.name = name or 'Generic'
        self.is_complete = Event()
        self.output = None

    def perform(self, input_queue, output_queue=None):
        if not self.is_complete.isSet():
            if self.name != 'Parsing':
                ###
                # Haha, there are like, 100000000 Parsing Tasks.
                ###
                logging.debug("Performing %s Task" % (self.name))
            self.output = self.func(*self.args, **self.kwargs)
            input_queue.task_done()
            if self.output and output_queue:
                logging.debug("Putting %s in %s" % (self.output, output_queue))
                output_queue.put_nowait(self.output)
            self.is_complete.set()
        return self.output

