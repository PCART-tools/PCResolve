from protocols import Child as ImportedManager


def root(**kwargs):
    with ImportedManager() as session:
        return session.request(**kwargs)
