import json
from urllib.request import Request, urlopen
from .models import TaskSpec


class MockModelClient:
    def generate(self, problem: TaskSpec, feedback: str | None, *, strategy: str = '') -> str:
        solutions = {'add': 'def add(a, b):\n    return a + b\n',
                     'reverse': 'def reverse(text):\n    return text[::-1]\n'}
        if problem.id not in solutions:
            raise ValueError('No mock solution for problem')
        return solutions[problem.id]


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30):
        if not base_url.startswith('https://'):
            raise ValueError('Model endpoint must use HTTPS')
        self.base_url, self.api_key, self.model, self.timeout = base_url.rstrip('/'), api_key, model, timeout

    def generate(self, problem: TaskSpec, feedback: str | None, *, strategy: str = '') -> str:
        prompt = (f'Solve this Python problem: {problem.description}\n'
                  f'Strategy guidance: {strategy}\nDefine the function {problem.function_name}. Return only executable Python code, '
                  f'no markdown or explanation.\nPrevious attempt feedback: {feedback or "none"}')
        return self.complete(prompt)

    def complete(self, prompt: str) -> str:
        body = json.dumps({'model': self.model, 'messages': [{'role': 'user', 'content': prompt}]}).encode()
        request = Request(self.base_url + '/chat/completions', data=body,
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key})
        with urlopen(request, timeout=self.timeout) as response:
            content = json.loads(response.read())['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Model returned empty code')
        return content
