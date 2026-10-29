# EvoLoop

## 题集和持续集成

项目保留 4 道 `demo` 演示题，另提供人工编写的 `core` 题集：24 道题、156 个测试用例，固定分成 16 道开发题和 8 道保留题。覆盖字符串、序列、映射、数值、搜索、区间、解析、矩阵及动态规划。题目描述包含函数签名和返回约定；详细说明见 [题集说明](docs/benchmarks/python-core-v1.md)。

无需密钥即可查看题集 ID、数量和内容哈希：

```powershell
python -m evoloop --list-benchmarks
```

配置真实模型后，可显式选择新题集。两轮实验在每题均达到三次尝试的保守上限下最多需要 194 次模型调用；示例将预算设为 200，不会自动提高默认的 100 次上限：

```powershell
python -m evoloop --improve --benchmark core --model openai-compatible --rounds 2 --max-model-calls 200 --state-dir runs/core-v1
```

`mock` 客户端只支持 `demo`，不能用其预设答案对 `core` 评分。新题集有独立的可信参考实现，位于 `tests/reference_solutions.py`，只用于验证预期结果和 Docker 判题，不会打包进运行时或发给模型。这仍是小规模功能评测题集，未证明真实模型的改进效果，也不保证算法时间复杂度或统计显著性；保留集只在接口层对策略提议器隐藏，仓库中的题目本身是公开的。

GitHub Actions 会在 push、PR 和手动触发时，在 Ubuntu 上对 Python 3.12、3.13、3.14 运行全套 pytest。每个任务先检查 Docker、准备镜像并检查 wheel 题集资源，然后验证全部 24 个参考解答和原有端到端流程；JUnit 报告会作为运行附件保存。工作流不需要模型密钥，使用只读仓库权限和固定的官方 Action 提交版本。

本机缺少 Docker 时会跳过集成测试；CI 设置 `EVOLOOP_REQUIRE_DOCKER=1`，缺少引擎或镜像时必须失败。可在本机仅运行不依赖容器的测试：`python -m pytest -m "not integration" -q`。要强制完整验证，在 PowerShell 设置 `$env:EVOLOOP_REQUIRE_DOCKER='1'` 后运行 `python -m pytest -q`，结束后可用 `Remove-Item Env:EVOLOOP_REQUIRE_DOCKER` 清除设置。

## 第二阶段：模拟策略自改进

现已提供有预算上限的策略实验。无需 API 密钥，使用明确标注的模拟客户端生成代码，并在真实 Docker 容器中评测：

```powershell
New-Item -ItemType Directory -Force runs | Out-Null
python -m evoloop --improve --model mock --rounds 2 --max-model-calls 100 --state-dir runs/demo > runs/demo-report.json
```

默认策略在合成开发题集上失败，模拟提议器返回预设的边界条件指导，新策略在开发集提升后才进入保留集比较。开发集必须严格提升，保留集不能退步，才写入 `runs/demo/active_strategy.json`。这是人为构造的流程演示，不代表模型训练或真实推理能力提高。

状态目录还包含 `reports/<run_id>.json` 和 `strategies/<strategy_id>.json`。报告记录题集与分集哈希、模型和执行参数、父策略、每轮候选和拒绝原因、全部代码尝试、首次通过率、最终通过率、调用数及耗时。`promotion_eligible` 表示评测允许晋升，`persisted` 表示保存成功；实际当前策略以 `active_strategy.json` 为准。每次实验先保存报告和档案，最后原子替换当前策略；写入失败返回非零并保留旧策略。状态目录只支持单进程写入。

重复运行同一命令将加载当前策略作为新基线；通常返回 `no_improvement`，表示没有更优候选，不是程序错误。使用新的状态目录可重新演示首次晋升。所有运行产物都应保留在 Git 忽略的 `runs/` 中。

每题最多 3 次尝试；改进轮数为 1–5，默认 2；默认最多 100 次模型调用，提议和生成答案均计费，失败调用也消耗预算。预算不足、模型错误或执行基础设施错误会终止实验并禁止晋升。CLI 退出码 0 表示实验完整并保存成功（包括候选被拒绝），1 表示实验未完成或存储失败，2 表示配置或参数错误。

模型只接收公共题目描述和函数名；测试只交给执行器，策略提议器只接收经过筛选的开发反馈。所有候选冻结后，才各评测一次旧策略和候选的保留集表现。重复使用同一保留集仍可能产生间接过拟合；报告提供哈希以识别复用。

普通示例解题支持显式策略文件：`python -m evoloop --strategy-file runs/demo/active_strategy.json`。真实服务仍使用 `.env` 配置，可通过 `--improve --model openai-compatible` 使用同一实验接口；当前真实模型效果未经验证。

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
