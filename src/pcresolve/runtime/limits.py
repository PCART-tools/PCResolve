## @package pcresolve.runtime.limits
#  Opt-in cooperative whole-analysis limits, separate from semantic proof budgets.
#  可选的全分析协作式资源限制，与语义证明预算分离。

import math
import os
import time
from dataclasses import dataclass
from typing import Optional


## Requested time, work and resident-memory limits; None means unrestricted.
## 指定的时间、工作量和驻留内存限制；None 表示不限制。
@dataclass(frozen=True)
class AnalysisLimits:
    ## Cooperative elapsed-time limit for one analyze() call.
    max_seconds: Optional[float] = None
    ## Total charged files, syntax nodes, records and resolver entries.
    max_work: Optional[int] = None
    ## Resident-memory ceiling checked at analysis checkpoints.
    max_memory_mb: Optional[float] = None

    ## Validate that limits are finite and positive and work is integral.
    ## 验证限制为有限正数，且工作量限制为整数。
    #
    #  @return None; invalid limits raise ValueError.
    def __post_init__(self):
        for value in (self.max_seconds, self.max_work, self.max_memory_mb):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError('Analysis limits must be finite and positive')
        if self.max_work is not None and int(self.max_work) != self.max_work:
            raise ValueError('Analysis work limit must be an integer')


## Analysis stopped at an explicit resource boundary; no partial proof is returned.
## 分析在显式资源边界停止，不返回部分证明。
class AnalysisLimitExceeded(RuntimeError):
    ## Identify the exceeded resource and observed work counter.
    ## 记录超限资源及当时的工作量计数。
    #
    #  @param reason Exceeded resource or unavailable memory counter.
    #  @param work Work units observed when stopped.
    #  @return None
    def __init__(self, reason, work):
        self.reason, self.work = reason, work
        super().__init__('Analysis %s limit exceeded after %d work units' % (reason, work))


## Read current resident memory on Windows/Linux, peak resident memory elsewhere.
## 在 Windows/Linux 读取当前驻留内存，在其他平台读取峰值驻留内存。
#
#  @return Bytes or None when the platform cannot supply a counter.
def resident_memory():
    if os.name == 'nt':
        import ctypes
        ## Windows process memory counters returned by GetProcessMemoryInfo.
        ## GetProcessMemoryInfo 返回的 Windows 进程内存计数器。
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
## 单次运行的工作计数和摊销资源检查。
class AnalysisBudget:
    ## Initialize fresh counters; clocks/readers may be supplied for deterministic tests.
    ## 初始化计数器；可注入时钟和读取器以便确定性测试。
    #
    #  @param limits Explicit AnalysisLimits.
    #  @param clock Monotonic time reader.
    #  @param memory Resident-memory reader returning bytes.
    #  @return None
    def __init__(self, limits, clock=time.monotonic, memory=resident_memory):
        self.limits, self.clock, self.memory = limits, clock, memory
        self.started, self.work, self._last_check = clock(), 0, 0

    ## Charge work and stop at an exceeded explicit resource limit.
    ## 计入工作量，并在超过显式资源限制时停止。
    #
    #  @param work Number of visited facts, syntax nodes or resolver entries.
    #  @param force Check time/memory even before the next 64-work checkpoint.
    #  @return None; an exceeded or unavailable limit raises AnalysisLimitExceeded.
    def checkpoint(self, work=1, force=False):
        self.work += work
        if self.limits.max_work is not None and self.work > self.limits.max_work:
            raise AnalysisLimitExceeded('work', self.work)
        if not force and self.work - self._last_check < 64:
            return

        # Amortize time and memory reads while checking the work limit every call.
        # 摊销时间和内存读取开销，同时每次调用都检查工作量限制。
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
