# IELTS AI Coach 项目交接说明

最后核对日期：2026-07-17

## 1. 当前结论

IELTS AI Coach 是一个使用 Streamlit、SQLAlchemy 和 SQLite 构建的本地
模块化应用。当前 V2.1 Phase 1 已完成第一个可用的 Academic 阅读练习闭环：

```text
今日任务
→ 开始或继续练习
→ 完成原创阅读题
→ 提交答案
→ 确定性评分
→ 查看逐题解析与原文证据
→ 保存历史
→ 同步任务状态和学习日志
```

当前自动化测试基线为 74 项。测试使用临时 SQLite 数据库和本地 Mock/Fake
Provider，不调用真实 Qwen API，也不读写默认运行数据库。

## 2. 已完成功能

### 账号与数据隔离

- 用户名和密码注册、登录、退出。
- 密码只保存 Argon2id 哈希。
- 用户名按规范化值进行大小写不敏感的唯一性判断。
- Streamlit Session 只保存必要的登录状态。
- 业务查询和修改都使用认证 Session 中的 `user_id`，不信任页面输入的用户 ID。

### 学习档案、成绩和计划

- 学生档案、目标分、考试日期和每日学习时长。
- IELTS 四科成绩历史和确定性 Overall 计算。
- 并列弱项识别和规则化中文建议。
- 确定性七天计划、任务内容、完成状态和实际学习日志。
- 计划重新生成时归档旧版本，不覆盖历史。

### 原创阅读练习

- 版本化题库位于
  `ielts_ai_coach/content/question_banks/reading_v1.json`。
- 第一版包含 3 篇项目原创 Academic 阅读文章，每篇 9 题。
- 题型包括 Multiple Choice、True/False/Not Given 和 Matching Heading。
- 每题保存题目、选项、正确答案、解析和原文证据。
- 提交前不渲染答案、解析或证据。
- 答案按 Unicode、大小写和连续空格进行规范化后确定性判分，不调用 AI。
- 最终提交保存得分、正确率、错题编号、答案和复盘快照。
- 一个任务只允许一次最终提交；重复提交不会覆盖历史。
- 提交、任务完成和学习日志同步在同一事务中完成。

原创IELTS风格练习，非官方IELTS或Cambridge试题。

### AI 与写作

- Provider 接口隔离外部 AI 调用。
- 未配置 API Key 时自动使用 Mock 演示模式。
- Qwen 模式使用兼容 OpenAI Chat Completions 的 Provider。
- AI 教练和写作反馈有成功次数限制；失败调用不计入成功额度。
- 写作反馈为学习用途的 AI 预估，不等同于官方考官评分。
- 自动化测试不得调用真实 AI API。

### Dashboard、历史和数据控制

- Dashboard 展示目标、成绩、任务进度、学习时间、趋势和 AI 额度。
- 历史页汇总成绩、计划、阅读结果、作文和教练记录。
- 用户只能清理自己的可选学习数据或 AI 内容，并需要二次确认。
- 本地 SQLite 每日在线备份，保留数量受配置控制。

## 3. 活动架构

```text
app.py
└── ielts_ai_coach/
    ├── auth.py              认证规则
    ├── config.py            环境与 Secrets 配置
    ├── views/               中文界面和页面流程
    ├── services/            业务规则和流程编排
    ├── database/            SQLAlchemy 模型与 Repository
    ├── ai/                  Qwen、Mock 和响应结构校验
    └── content/
        └── question_banks/  版本化原创题库
```

页面只负责展示和流程控制。SQL 位于数据库层，评分、计划、提交和额度规则位于
Service 层，外部 AI HTTP 调用位于 Provider 后面。

根目录中的旧 MVP 模块尚未获准归档，不能擅自删除。历史企业原型
`archive/enterprise-v0/` 只用于保留参考，禁止修改、导入、测试或提交。

## 4. 数据库

本地开发默认使用 SQLite，连接地址由 `DATABASE_URL` 配置。表结构通过
SQLAlchemy `create_all` 补充；不删除旧表，不修改旧字段，不清空旧数据。

当前活动模型共有 11 张表：

1. `users`
2. `student_profiles`
3. `score_records`
4. `study_plans`
5. `plan_tasks`
6. `study_logs`
7. `coach_messages`
8. `ai_usage_daily`
9. `essays`
10. `writing_feedback`
11. `task_question_attempts`

运行数据库、WAL/SHM、备份和测试临时数据库都不得提交到 Git。交接文档不记录
真实用户、作文、学习记录或各表行数。

## 5. 本地运行

要求 Python 3.12.x：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

不配置 `QWEN_API_KEY` 时会使用 Mock 模式。私密配置只能写入环境变量或
`.streamlit/secrets.toml`，不能写入示例文件、代码、截图或 Git。

## 6. 验证

基础命令：

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pip check
```

当前 74 项测试覆盖：

- 认证、密码哈希和 Session 安全；
- 用户隔离和数据清理边界；
- 成绩、计划、任务和学习日志；
- 题库加载和版权来源约束；
- 三种阅读题型、答案规范化和错误反馈；
- 漏答、重复提交、跨用户提交和历史保存；
- Streamlit 开始、继续、提交和结果页面流程；
- Mock/Qwen Provider 边界、额度和写作反馈；
- 备份、Dashboard 和完整学生流程。

完成修改后还应进行无界面 Streamlit 启动和 HTTP 健康检查。验收应使用临时
数据库并显式保持 Mock 模式。

## 7. Git 与隐私边界

允许提交的核心内容包括应用代码、原创题库、测试、说明文档、示例配置和依赖
声明。以下内容必须留在本地并由 `.gitignore` 排除：

- `.env` 和 `.streamlit/secrets.toml`；
- SQLite 数据库、WAL/SHM 和备份；
- 日志、上传文件、缓存和虚拟环境；
- `archive/enterprise-v0/`；
- 未裁剪、仍包含浏览器或桌面环境信息的本地截图。

示例配置只能包含空值或占位值。本地截图在裁剪浏览器书签、桌面任务栏等环境
信息并确认只使用虚构学生数据后，才适合单独加入。

## 8. 当前限制

- SQLite 只适合当前本地阶段，不是公网多实例数据库方案。
- 原创阅读题库目前只有 3 篇，每个任务只允许一次最终提交。
- 听力没有内置原创音频练习闭环。
- AI 调用是同步的，写作预估尚未经过官方考官校准。
- 没有口语录音、用户上传、账号自删除、密码修改、支付或教师后台。
- 没有生产监控、托管备份、正式迁移或云部署。

## 9. 建议的下一阶段

先使用虚构或明确同意的数据做阅读闭环易用性测试，再决定是否增加重试机制和
扩充原创题库。原创听力脚本、AI 上下文增强、Dashboard 升级、用户上传、
数据库迁移和云部署都应分别获得批准后再开始。
