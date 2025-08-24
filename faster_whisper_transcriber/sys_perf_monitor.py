# pip install nvidia-ml-py3 psutil
import psutil
import pynvml as nvml

def _get_running_procs(handle):
    procs = []
    # 计算进程（CUDA 计算）
    for fname in ("nvmlDeviceGetComputeRunningProcesses_v3",
                  "nvmlDeviceGetComputeRunningProcesses_v2",
                  "nvmlDeviceGetComputeRunningProcesses"):
        if hasattr(nvml, fname):
            try:
                procs.extend(getattr(nvml, fname)(handle))
                break
            except nvml.NVMLError:
                pass
    # 图形进程（OpenGL/显示）
    for fname in ("nvmlDeviceGetGraphicsRunningProcesses_v3",
                  "nvmlDeviceGetGraphicsRunningProcesses_v2",
                  "nvmlDeviceGetGraphicsRunningProcesses"):
        if hasattr(nvml, fname):
            try:
                procs.extend(getattr(nvml, fname)(handle))
                break
            except nvml.NVMLError:
                pass
    return procs

def bytes_to_mib(b):
    return b / (1024**2)

def main():
    nvml.nvmlInit()
    try:
        count = nvml.nvmlDeviceGetCount()
        for i in range(count):
            h = nvml.nvmlDeviceGetHandleByIndex(i)
            name = nvml.nvmlDeviceGetName(h).decode() if isinstance(nvml.nvmlDeviceGetName(h), bytes) else nvml.nvmlDeviceGetName(h)
            mem = nvml.nvmlDeviceGetMemoryInfo(h)
            print(f"GPU {i}: {name}")
            print(f"  Memory: total={bytes_to_mib(mem.total):.0f} MiB, "
                  f"used={bytes_to_mib(mem.used):.0f} MiB, free={bytes_to_mib(mem.free):.0f} MiB")

            procs = _get_running_procs(h)
            if not procs:
                print("  No running GPU processes.")
            else:
                print("  Processes using VRAM:")
                for p in procs:
                    pid = p.pid
                    used_mib = bytes_to_mib(getattr(p, "usedGpuMemory", 0))
                    pname = "<unknown>"
                    try:
                        pname = psutil.Process(pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    print(f"    PID {pid:<8} {pname:<30} used={used_mib:.0f} MiB")
            print()
    finally:
        nvml.nvmlShutdown()
        
        
import torch
def torch_main():
    m_a = torch.cuda.memory_allocated(0)        # 当前进程已分配
    m_max_a=torch.cuda.max_memory_allocated(0)
    m_reserve=torch.cuda.memory_reserved(0)         # caching allocator 已保留
    print(f'memory_allocated:{m_a},max_memory_allocated:{m_max_a},memory_reserved:{m_reserve}')

# pip install gputil
import GPUtil
def padding(s, pad_len:int=10):
    return str(s).ljust(pad_len,' ').rjust(pad_len, ' ')

def gputil_main():
    for gpu in GPUtil.getGPUs():
        print(padding(gpu.id), padding(gpu.name,30), padding(gpu.memoryTotal,15), padding(gpu.memoryUsed,15), padding(gpu.memoryFree))


if __name__ == "__main__":
    from datetime import datetime
    import time
    
    while True:
        print(f'\n\nnow: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        # main()
        # torch_main()
        print(padding("gpu.id"), padding("gpu.name",30), padding("gpu.memoryTotal",15), padding("gpu.memoryUsed",15), padding("gpu.memoryFree"))
        gputil_main()
        time.sleep(3)