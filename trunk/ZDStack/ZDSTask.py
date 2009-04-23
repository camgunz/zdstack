from threading import Event

from ZDStack import get_zdslog

zdslog = get_zdslog()

class Task(object):

    """Represents a Task to be performed.

    .. attribute:: func
        The function this Task will call when it is performed

    .. attribute:: args
        A list of positional arguments to pass to func

    .. attribute:: kwargs
        A list of keyword arguments to pass to func

    .. attribute:: name
        The (optional) name of this task, default 'Generic'

    .. attribute:: is_complete
        An Event that is set when this task is complete

    .. attribute:: output
        The return value (if any) of func after it's called, starts off
        as None, and may remain so

    """

    def __init__(self, func, args=None, kwargs=None, name=None):
        """Initializes a Task.

        :param func: what this Task calls when it's performed
        :type func: function

        :param args:
            A list of positional arguments to pass to func, default None

        :param kwargs:
            A list of keyword arguments to pass to func, default None

        :param name:
            The (optional) name of this task, defaults 'Generic'

        """
        self.func = func
        self.args = args or list()
        self.kwargs = kwargs or dict()
        self.name = name or 'Generic'
        self.is_complete = Event()
        self.output = None

    def perform(self, input_queue, output_queue=None):
        """Performs this Task.

        :param input_queue: the queue from which this task was created
        :type input_queue: Queue.Queue
        :param output_queue: optional, the queue in which to place the
                             output of self.func
        :type output_queue: Queue.Queue
        :returns: the output of self.func

        """
        if not self.is_complete.isSet():
            if self.name != 'Parsing':
                ###
                # Haha, there are like, 100000000 Parsing Tasks.
                ###
                zdslog.debug("Performing %s Task" % (self.name))
            self.output = self.func(*self.args, **self.kwargs)
            input_queue.task_done()
            if self.output and output_queue:
                zdslog.debug("Putting %s in %s" % (self.output, output_queue))
                output_queue.put_nowait(self.output)
            self.is_complete.set()
        return self.output

