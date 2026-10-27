import json
import subprocess
import time
import uuid
from dataclasses import asdict
from .models import ExecutionResult, Problem, Status

# This script runs only inside the container, never in the application process.
_RUNNER = r'''
import json, os, sys
payload = json.load(sys.stdin)
out = os.dup(1)
null = os.open('/dev/null', os.O_WRONLY)
os.dup2(null, 1)
os.dup2(null, 2)
try:
    namespace = {}
    exec(compile(payload['code'], '<solution>', 'exec'), namespace)
    fn = namespace[payload['function_name']]
    for index, test in enumerate(payload['tests'], 1):
        if fn(*test['args']) != test['expected']:
            os.write(out, ('EVOL_RESULT:failed:%d\n' % index).encode())
            break
    else:
        os.write(out, b'EVOL_RESULT:passed:0\n')
except BaseException:
    os.write(out, b'EVOL_RESULT:error:0\n')
'''


class DockerExecutor:
    def __init__(self, image: str = 'python:3.12-alpine', timeout: float = 5):
        if timeout <= 0:
            raise ValueError('timeout must be positive')
        self.image, self.timeout = image, timeout

    def run(self, problem: Problem, code: str) -> ExecutionResult:
        start = time.monotonic()
        name = 'evoloop-' + uuid.uuid4().hex
        cmd = ['docker', 'run', '--rm', '-i', '--name', name, '--pull=never',
               '--network=none', '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges', '--pids-limit=32',
               '--memory=128m', '--cpus=0.5', '--user=65534:65534',
               '--tmpfs=/tmp:rw,noexec,nosuid,size=4m', self.image,
               'python', '-I', '-c', _RUNNER]
        payload = json.dumps({'code': code, 'function_name': problem.function_name,
                              'tests': [asdict(t) for t in problem.tests]})
        try:
            process = subprocess.run(cmd, input=payload, text=True, capture_output=True, timeout=self.timeout)
        except FileNotFoundError:
            return ExecutionResult(Status.UNAVAILABLE, time.monotonic() - start, 'Docker unavailable')
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
            return ExecutionResult(Status.TIMEOUT, time.monotonic() - start, 'Execution timed out')
        elapsed = time.monotonic() - start
        if process.returncode == 125 or 'failed to connect to the docker api' in process.stderr.lower():
            return ExecutionResult(Status.UNAVAILABLE, elapsed, 'Docker unavailable or image missing')
        if process.returncode != 0:
            return ExecutionResult(Status.ERROR, elapsed, 'Container execution failed')
        output = process.stdout.strip()
        if output == 'EVOL_RESULT:passed:0':
            return ExecutionResult(Status.PASSED, elapsed)
        if output.startswith('EVOL_RESULT:failed:'):
            number = output.removeprefix('EVOL_RESULT:failed:')
            if number.isdecimal() and 1 <= int(number) <= len(problem.tests):
                return ExecutionResult(Status.FAILED, elapsed, f'case {int(number)} failed')
        return ExecutionResult(Status.ERROR, elapsed, 'Code raised an exception or produced an invalid result')
