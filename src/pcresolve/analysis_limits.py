## @package pcresolve.analysis_limits
#  Opt-in cooperative whole-analysis limits, separate from semantic proof budgets.

import math
import os
import time
from dataclasses import dataclass
from typing import Optional


## Requested time, work and resident-memory limits; None means unrestricted.
@dataclass(frozen=True)
class AnalysisLimits:
    ## Cooperative elapsed-time limit for one analyze() call.
    max_seconds: Optional[float] = None
    ## Total charged files, syntax nodes, records and resolver entries.
    max_work: Optional[int] = None
    ## Resident-memory ceiling checked at analysis checkpoints.
    max_memory_mb: Optional[float] = None

    def __post_init__(self):
        for value in (self.max_seconds, self.max_work, self.max_memory_mb):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError('Analysis limits must be finite and positive')
        if self.max_work is not None and int(self.max_work) != self.max_work:
            raise ValueError('Analysis work limit must be an integer')


## Analysis stopped at an explicit resource boundary; no partial proof is returned.
class AnalysisLimitExceeded(RuntimeError):
    ## Identify the exceeded resource and observed work counter.
    def __init__(self, reason, work):
        self.reason, self.work = reason, work
        super().__init__('Analysis %s limit exceeded after %d work units' % (reason, work))


## Read current resident memory on Windows/Linux, peak resident memory elsewhere.
#  @return Bytes or None when the platform cannot supply a counter.
def resident_memory():
    if os.name == 'nt':
        import ctypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong),
                        ('peak', ctypes.c_size_t), ('rss', ctypes.c_size_t),
                        ('paged_peak', ctypes.c_size_t), ('paged', ctypes.c_size_t),
                        ('nonpaged_peak', ctypes.c_size_t), ('nonpaged', ctypes.c_size_t),
                        ('pagefile', ctypes.c_size_t), ('pagefile_peak', ctypes.c_size_t)]
        value = Counters()
        value.cb = ctypes.sizeof(value)
        process = ctypes.windll.kernel32.GetCurrentProcess
        process.restype = ctypes.c_void_p
        read = ctypes.windll.psapi.GetProcessMemoryInfo
        read.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        return int(value.rss) if read(process(), ctypes.byref(value), value.cb) else None
    try:
        if os.path.exists('/proc/self/statm'):
            with open('/proc/self/statm', encoding='ascii') as stream:
                return int(stream.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
        import resource
        import sys
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value) * (1 if sys.platform == 'darwin' else 1024)
    except (OSError, ImportError, ValueError, IndexError):
        return None


## One run's work counter and amortized resource checks.
class AnalysisBudget:
    ## Initialize fresh counters; clocks/readers may be supplied for deterministic tests.
    #  @param limits Explicit AnalysisLimits.
    #  @param clock Monotonic time reader.
    #  @param memory Resident-memory reader returning bytes.
    def __init__(self, limits, clock=time.monotonic, memory=resident_memory):
        self.limits, self.clock, self.memory = limits, clock, memory
        self.started, self.work, self._last_check = clock(), 0, 0

    ## Charge work and stop at an exceeded explicit resource limit.
    #  @param work Number of visited facts, syntax nodes or resolver entries.
    #  @param force Check time/memory even before the next 64-work checkpoint.
    def checkpoint(self, work=1, force=False):
        self.work += work
        if self.limits.max_work is not None and self.work > self.limits.max_work:
            raise AnalysisLimitExceeded('work', self.work)
        if not force and self.work - self._last_check < 64:
            return
        self._last_check = self.work
        if (self.limits.max_seconds is not None
                and self.clock() - self.started > self.limits.max_seconds):
            raise AnalysisLimitExceeded('time', self.work)
        if self.limits.max_memory_mb is not None:
            measured = self.memory()
            if measured is None:
                raise AnalysisLimitExceeded('memory counter unavailable', self.work)
            if measured > self.limits.max_memory_mb * 1024 * 1024:
                raise AnalysisLimitExceeded('memory', self.work)
