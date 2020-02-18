import os
import tensorflow as tf
import numpy as np
from tensorflow.python import pywrap_tensorflow
from tensorflow.python.util import compat
from tensorflow.core.util import event_pb2
import time


def ensure_dir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)


class Logger(object):
    @staticmethod
    def convert_np_to_py(v):
        if type(v).__module__ == np.__name__:
            return float(np.asscalar(v))
        else:
            return v

    def __init__(self, log_fields=None, log_path=None, step_field=None):
        self.log_fields = log_fields
        self.log_path = log_path
        self.step_field = step_field
        self.writer = None
        if log_path is not None:
            self.fallback_step = 1
            prefix = 'events'
            path = os.path.join(os.path.abspath(log_path), prefix)
            print("events_path: ", path)
            ensure_dir(path)
            self.writer = pywrap_tensorflow.EventsWriter(compat.as_bytes(path))

    def writekvs(self, kvs, step):
        if self.writer is not None:

            def summary_val(k, v):
                kwargs = {'tag': k, 'simple_value': float(v)}
                return tf.Summary.Value(**kwargs)

            summary = tf.Summary(value=[
                summary_val(k, v) for k, v in kvs
                if isinstance(v, float) or isinstance(v, int)
            ])
            event = event_pb2.Event(wall_time=time.time(), summary=summary)
            event.step = step  # is there any reason why you'd want to specify the step?
            # Yes, the step is shown in TensorBoard.
            self.writer.WriteEvent(event)
            self.writer.Flush()

    def log(self, variables):
        if self.log_fields is not None:
            log_values = [variables[field] for field in self.log_fields]
            pairs = zip(self.log_fields, log_values)
        else:
            pairs = variables.items()
        pairs = sorted([(k, self.convert_np_to_py(v)) for k, v in pairs])
        max_len = max([len(k) for k, v in pairs])
        step = int(variables[self.step_field]) if self.step_field else self.fallback_step
        # KeyError intended when step_field given, but not available in variables.
        self.writekvs(pairs, step=step)
        self.fallback_step += 1
        print()
        print('=' * 40)
        #print('%s : %s'%('name'.ljust(max_len), self.name))
        for field, value in pairs:
            if isinstance(value, float):
                print('%s : %.6f' % (field.ljust(max_len), value))
            elif isinstance(value, int):
                print('%s : %d' % (field.ljust(max_len), value))
            elif isinstance(value, str):
                print('%s : %s' % (field.ljust(max_len), value))
            else:
                print(type(value))
                raise NotImplementedError
        print('=' * 40)
        print()
