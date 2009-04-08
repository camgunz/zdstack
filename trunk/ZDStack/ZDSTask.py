from threading import Event

class Task(object):

    def __init__(self, func):
        self.func = func
        self.complete = Event()
        self.output = None

    def perform(self, input_queue, output_queue=None):
        if not self.complete.isSet():
            self.output = self.func()
            input_queue.task_done()
            if self.output and output_queue:
                place_output_in_queue.put_nowait(self.output)
            self.complete.set()
        return self.output

