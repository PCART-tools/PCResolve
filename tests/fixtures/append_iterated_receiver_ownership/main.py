from multiprocessing import Process


def run():
    pass


def wait_for_workers():
    workers = []
    workers.append(Process(target=run))
    for worker in workers:
        worker.join()


def wait_for_mixed_workers():
    workers = []
    workers.append(Process(target=run))
    workers.append(run)
    for worker in workers:
        worker.join()
