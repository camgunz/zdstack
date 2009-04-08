from threading import Event

class Task(object):

    def __init__(self, func):
        self.func = func
        self.complete = Event()
        self.output = None

    def __call__(self):
        return self.perform()

    def perform(self):
        if not self.complete.isSet():
            self.output = self.func()
            self.complete.set()
        return self.output

