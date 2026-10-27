# EvoLoop — 第一阶段

最小 Python 编程题 Agent：可替换模型客户端和执行器、最多三次尝试、JSON 报告。默认模型是离线模拟客户端，不需要密钥。

## 安装与运行

需要 Python 3.12+、Docker（Linux 容器模式）及可运行的 Docker 引擎。启动 Docker Desktop 后，在项目目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
docker pull python:3.12-alpine
python -m evoloop > report.json
python -m pytest -q
```

报告标准输出为 JSON；退出码 0 表示所有题目通过，1 表示至少一题未通过或容器不可用，2 表示模型配置不完整。结果含每次尝试的题目 ID、代码、状态、总耗时（模型调用加判题）和错误摘要。执行器不可用时立即停止，不将环境故障反馈给模型重复生成。

模拟客户端只提供内置示例题答案。接入支持 Chat Completions 协议的服务：将 `.env.example` 复制为 `.env`，填写 `EVOLOOP_BASE_URL`（HTTPS，通常以 `/v1` 结尾）、`EVOLOOP_MODEL`、`EVOLOOP_API_KEY`，然后执行：

```powershell
python -m evoloop --model openai-compatible > report.json
```

`.env` 已被 Git 忽略，绝不要提交真实密钥。可自行实现 `ModelClient.generate` 和 `CodeExecutor.run` 协议替换组件。题目测试输入和期望值须为 JSON 兼容类型。

## 隔离与限制

判题使用独立 Docker 容器：无网络、只读根文件系统、无宿主挂载、非 root、移除 Linux capabilities，限制内存、CPU 和进程数，超时后强制删除容器。没有 Docker 或镜像时不会在宿主进程执行代码。容器本身共享宿主内核，不能当作抵御恶意代码的强隔离；生产环境应使用专用虚拟机或更强的沙箱，并限制输出、磁盘、容器生命周期和 Docker 守护进程权限。当前评测程序和生成代码同处容器进程，恶意代码可能干扰评测结果，因此只适用于受控实验，不应作为对抗性评测或安全边界。超时清理依赖 Docker 守护进程可用。

集成测试需要本地镜像和运行中的引擎，否则跳过；单元测试使用替身验证编排和 Docker 调用，不能代替真实容器验证。
