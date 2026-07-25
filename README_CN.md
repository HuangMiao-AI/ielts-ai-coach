# IELTS AI Coach

IELTS AI Coach 是一个本地运行的雅思学习应用，面向中文学习者。项目使用
Python、Streamlit、SQLAlchemy 和 SQLite，重点提供可验证的练习流程、确定性
评分与可选的 AI 学习辅助。

## 当前功能

- 使用 Argon2id 保存密码，并按已登录用户严格隔离数据。
- 四步新手设置与可编辑学习档案；成绩可以留空，系统不会编造成绩。
- 确定性的成绩诊断和七天学习计划。
- 8 篇原创 Academic 阅读文章：答题、确定性评分、证据解析与历史记录。
- 2 套原创本地听力小测，含离线音频、确定性答案解析。当前版本的听力结果只在
  浏览器会话内保存。
- 4 道原创写作题。未启用 AI 评分时，作文会保存，但不会伪造成绩或反馈。
- 口语 Part 1/2/3 题目、计时、麦克风指引和文字替代；不提供自动评分。
- 按当前用户隔离的首页、学习分析、历史记录和学习日志，以及本地 Mock AI 说明。
- 手机、平板和桌面响应式界面；包含 PWA 元数据，但不承诺离线使用。

## 技术栈

- Python 3.12
- Streamlit
- SQLAlchemy 2 与 SQLite
- `argon2-cffi`（Argon2id）
- Pydantic 2
- pytest

## 安装与本地启动

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

在浏览器打开 `http://127.0.0.1:8501`。

### 手机局域网访问

在可信的家庭或教室 Wi-Fi 中运行：

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0
```

用 `ipconfig` 查看电脑的私有 IPv4 地址，再在同一 Wi-Fi 的手机上打开
`http://<私有IPv4地址>:8501`。这是本地开发服务，不应直接暴露到公网。

## Mock 与 Qwen 模式

没有配置凭据时，应用使用本地、确定性的 Mock Provider，不会调用真实 AI API。
如需使用 Qwen 兼容 Provider，只能通过环境变量或
`.streamlit/secrets.toml` 提供私有配置，不能把真实密钥写入代码或 Git。

AI 反馈和任何写作预估分仅供学习参考，不是官方 IELTS 成绩，也不能替代官方考官。

## 数据库说明

默认数据库为 `data/ielts_ai_coach.db`，不会被 Git 跟踪。项目使用
`create_all` 做本地的新增式建表。

`learner_profiles_v2` 是新增的学习档案表，包含唯一 `user_id`、昵称、年级、
可空考试日期、每日学习时间、目标分、可空的四科基线分、完成状态和时间戳。

- 未知成绩使用 SQL `NULL` / Python `None` 表示；真实的 `0` 会保留为 `0`。
- 读取时优先使用 `learner_profiles_v2`；没有 V2 记录才兼容读取旧
  `student_profiles`。
- 不会在启动时批量回填旧用户；旧用户只会在主动保存 Profile 后创建 V2 记录。
- `score_records` 只保存真实且完整的考试或练习成绩，不保存新手设置基线分。

数据库、WAL/SHM、备份、私有密钥、上传文件、日志和虚拟环境都不得提交到 Git。

## 版权声明

**原创IELTS风格练习，非官方IELTS或Cambridge试题。**

仓库内的阅读、听力和写作材料均为项目原创练习材料，不是官方 IELTS 或
Cambridge 真题。

## 测试

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q ielts_ai_coach
.venv\Scripts\python.exe -m pip check
```

当前基线为 **247 项 pytest 测试通过**。测试使用独立临时 SQLite 数据库和
Mock/fake Provider，不会调用真实 AI API。

## 当前限制

- SQLite 适合本地单实例开发，不适合公网多实例部署。
- 听力答案和得分只保存在当前会话，暂不进入学习分析历史。
- 口语录音与文字替代只保存在当前会话；没有语音识别、发音分析或自动分数。
- 无 Key/Mock 模式下保存的写作内容不会得到 AI 评分。
- PWA 仅提供安装元数据，没有 Service Worker 或完整离线能力。
- 当前不包含用户上传、原生 App、支付、云部署或数据库迁移。
