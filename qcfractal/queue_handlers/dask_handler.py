"""
Handlers for Dask
"""

import importlib
import logging
import operator


class DaskAdapter:
    def __init__(self, dask_server, logger=None):

        self.dask_server = dask_server
        self.queue = {}
        self.function_map = {}

        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger('DaskNanny')

    def get_function(self, function):
        if function in self.function_map:
            return self.function_map[function]

        module_name, func_name = function.split(".", 1)
        module = importlib.import_module(module_name)
        self.function_map[function] = operator.attrgetter(func_name)(module)

        return self.function_map[function]

    def submit_tasks(self, tasks):
        ret = []
        for task in tasks:

            tag = task["id"]
            if tag in self.queue:
                continue

            # Form run tuple
            func = self.get_function(task["spec"]["function"])
            job = self.dask_server.submit(func, *task["spec"]["args"], **task["spec"]["kwargs"])

            self.queue[tag] = (job, task["parser"], task["hooks"])
            self.logger.info("Adapter: Task submitted {}".format(tag))
            ret.append(tag)
        return ret

    def aquire_complete(self):
        ret = {}
        del_keys = []
        for key, (future, parser, hooks) in self.queue.items():
            if future.done():
                ret[key] = (future.result(), parser, hooks)
                del_keys.append(key)

        for key in del_keys:
            del self.queue[key]

        return ret

    def await_results(self):
        # Try to get each results
        [v[0].result() for k, v in self.queue.items()]
        return True

    def list_tasks(self):
        return list(self.queue.keys())

    def task_count(self):
        return len(self.queue)
