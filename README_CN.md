# IELTS AI Coach

## 项目简介

IELTS AI Coach 是一个面向中国雅思学生的模块化学习助手，也是一个
Computer Science / AI 大学申请作品。它把确定性成绩诊断、七天计划、每日
任务、学习记录、AI教练和写作批改整合在一个可维护的 Streamlit 应用中。
V2.1 Phase 1 已加入第一个可直接作答和自动评分的原创 Academic 阅读闭环。

> 写作页面中的分数均为 AI 预估，仅用于学习参考，不是官方 IELTS 成绩，
> 项目不承诺评分准确度。

## 功能

- 用户名和密码注册、登录、退出
- Argon2id 密码哈希和 Streamlit Session 用户隔离
- 学生档案：昵称、年级、目标分、考试日期、每日学习时间
- IELTS 四科历史成绩和确定性 Overall 计算
- 最低分、并列弱项、目标差距和规则化建议
- 每日分钟数严格相等的七天学习计划
- 含目标、材料、步骤、产出和完成标准的具体任务
- 3篇项目原创 Academic 阅读文章，每篇约800—1000词、9道题
- 覆盖 Multiple Choice、True/False/Not Given 和 Matching Heading
- 支持开始、暂存、继续、完整提交、确定性评分和逐题解析
- 保存答案、得分、正确率、错题、解析快照和完成时间
- 阅读提交后自动同步任务完成状态和学习日志
- 基础、专项提高、限时训练与模拟三个考试阶段
- 今日任务一键完成、可选修改实际用时、取消后同步撤销学习记录
- 旧计划自动归档，不删除历史
- Qwen 兼容 AI Provider；无 Key 时自动进入 Mock 演示模式
- AI学习教练：每天最多 20 次成功回答
- 写作批改 Level 2：四项预估分数、优点、问题、建议和单段改写
- 写作每天最多 3 次成功批改，失败不扣额度
- Dashboard、成绩趋势、学习时间、任务完成率和历史记录
- 顶部导航、手机页面内导航和按屏幕宽度响应的单列布局
- 二次确认后清理当前用户自己的学习数据或AI内容
- SQLite 每日在线备份，保留最近 7 份

## 架构

```text
app.py
  └── views/        中文界面和流程控制
       └── services/  验证、诊断、计划、额度和AI流程
            ├── database/  SQLAlchemy模型、Repository、备份
            └── ai/        Qwen、Mock、Pydantic结构校验
```

页面不执行 SQL，不验证密码，也不直接调用模型。所有业务查询都通过当前
登录用户的 `user_id` 隔离。学习计划和总分由确定性 Python 规则生成，即使
没有 AI API，核心学习功能仍然可用。

## 技术栈

- Python 3.12
- Streamlit 1.59
- SQLAlchemy 2.0 与 SQLite
- `argon2-cffi` 提供 Argon2id 密码哈希
- Pydantic 2 校验 AI 返回结构
- `requests` 通过 Provider 接口调用可选的 Qwen 服务
- pytest 8

## 本地运行

必须使用 Python 3.12.x：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

首次运行会创建 `data/ielts_ai_coach.db`，备份位于
`data/backups/`。这些文件不会上传 GitHub。

### 手机局域网访问

让 Streamlit 监听本机所有局域网接口：

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0
```

用 `ipconfig` 查看电脑的私有 IPv4 地址，再在连接同一可信 Wi-Fi 的手机上
打开 `http://<私有IP>:8501`。Windows 防火墙可能会询问是否允许局域网访问。
这是开发服务器，不应直接暴露到公网。

## Mock 与 Qwen 模式

默认无需配置 AI 服务。没有 API Key 时，AI 教练和写作反馈会清楚标记为
Mock 演示模式；档案、诊断、计划、任务、阅读评分、历史和 Dashboard 仍可用。

复制私密配置模板：

```powershell
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
```

在 `.streamlit/secrets.toml` 中填写：

```toml
QWEN_API_KEY = "你的私密API Key"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"
AI_TIMEOUT_SECONDS = "30"
AI_MAX_RETRIES = "2"
```

不同阿里云区域或工作空间可能使用不同 Base URL，请按账号对应的官方文档
配置。不要把真实 Key 写入代码、`.env.example`、截图或 GitHub。

配置真实 Key 后，只有自然语言教练和写作反馈走 Qwen 兼容 Provider。阅读
客观题、成绩诊断和七天计划仍由本地确定性规则完成。AI 写作预估不能替代
官方考官评分。

## 测试

```powershell
.venv\Scripts\python.exe -m pytest
```

测试使用临时 SQLite 数据库和本地假 Provider，不调用真实 AI API，也不会
污染 `data/`。当前共 74 项测试，包含题库加载、确定性评分、漏答、重复
提交、用户隔离、历史记录和真实 Streamlit 页面流程。

## 数据库说明

本地开发使用 SQLite，默认文件为 `data/ielts_ai_coach.db`。应用通过
SQLAlchemy `create_all` 补充缺失表，不删除旧表或旧字段。数据库、WAL/SHM、
备份和测试临时数据都不应进入 Git；测试也不会读写默认运行数据库。

## 数据安全

- 密码只保存 Argon2id 哈希。
- Session 不保存密码。
- 所有业务表都包含 `user_id`。
- 页面不接受用户自行填写 `user_id`。
- API Key、数据库、备份、日志、`.env` 和私密 Secrets 均被 Git 忽略。
- AI 上下文只使用当前用户必要的档案、成绩、计划和近期记录。
- 普通日志不记录完整作文。
- 删除功能只能清理当前账号的数据，并要求二次确认。

## 阅读题库与评分

第一版题库保存在版本化项目内容文件中。3篇文章及其题目、正确答案、解析和
原文证据均为项目原创，不复制官方 IELTS、Cambridge 或其他受版权保护真题。

**版权声明：原创IELTS风格练习，非官方IELTS或Cambridge试题。**

客观题评分完全由本地 Python 规则完成，不调用 AI。比较答案时会统一 Unicode、
大小写和连续空格。最终提交保存在 `task_question_attempts` 表中，并同时记录
得分、正确率、错题编号和完整复盘快照。

## 当前限制与下一步

本地版本使用 SQLite。当前原创阅读库只有3篇，每个任务只允许一次最终提交；
尚未实现阅读重试和更大规模轮换。听力仍使用学生合法拥有的材料，没有内置
原创音频闭环。AI 调用仍为同步处理，也尚未做官方考官校准、口语录音、支付、
教师/家长后台、账号自删除或密码修改。

下一步建议先测试阅读闭环的真实易用性，再扩充原创阅读题库；原创听力脚本和
音频应作为单独批准阶段。PostgreSQL、生产 Secrets、HTTPS 和云部署仍不属于
当前本地开发范围。

完整英文工程说明见 [README.md](README.md)。
