from external_base import Cache as ImportedCache

method = ImportedCache.__missing__
method.__code__ = unknown_code
