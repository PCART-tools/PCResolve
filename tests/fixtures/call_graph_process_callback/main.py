from multiprocessing import Process, Queue


def worker(options, index, jobs_queue, output_queue):
    jobs_queue.get()
    output_queue.put((index, options))


jobs_queue = Queue()
output_queue = Queue()
process = Process(
    target=worker,
    args=("options", 0, jobs_queue, output_queue),
)
