"""Run background media tools without opening console windows."""
import subprocess
import sys
from threading import Lock

_lock = Lock()
_processes = set()
_stopping = False


def stop_background_tools():
    """Kill running probes without waiting on the UI thread."""
    global _stopping
    with _lock:
        _stopping = True
        for process in tuple(_processes):
            try:
                process.kill()
            except OSError:
                pass


def run_background(command, **kwargs):
    kwargs.setdefault('stdin', subprocess.DEVNULL)
    if not kwargs.get('capture_output'):
        kwargs.setdefault('stdout', subprocess.DEVNULL)
        kwargs.setdefault('stderr', subprocess.DEVNULL)
    if sys.platform == 'win32':
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
    capture_output = kwargs.pop('capture_output', False)
    if capture_output:
        kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    timeout = kwargs.pop('timeout', None)
    check = kwargs.pop('check', False)
    with _lock:
        if _stopping:
            raise RuntimeError('Application is closing')
        process = subprocess.Popen(command, **kwargs)
        _processes.add(process)
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        if check and process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        with _lock:
            _processes.discard(process)
