# Codex Gmail 日报自动化设计

## 背景

当前 AI 开发者日报由 GitHub Actions 定时运行，使用 OpenRouter 完成中文总结，并通过 SMTP 发送邮件。OpenRouter Token 耗尽后，流水线只能发送基础版内容，无法继续提供 AI 增强摘要。

本次改造将内容生成迁移到 Codex 桌面端定时任务，并使用已连接的 Gmail 插件直接发信。现有 Python 项目继续负责信息采集、排序、历史去重和报告归档，不再依赖 OpenRouter 才能完成定时日报。

## 目标

- 每周一、周三北京时间 07:00 自动生成并发送 AI 开发者日报。
- 使用 Codex 自身模型生成中文摘要，不消耗 OpenRouter Token。
- 从 `rockyyang951225@gmail.com` 发送给 `rockyyang951225@gmail.com` 和 `zoeyli1997@gmail.com`。
- 保留现有信息来源、排序规则、14 天历史去重和 `skills.sh` 数据源。
- 将生成的 Markdown 报告保存到 `reports/` 并推送到远程仓库。
- 停用旧 GitHub Actions 定时生成和发信，避免重复邮件；保留手动触发作为备用。

## 非目标

- 不迁移或复制 GitHub Secrets 中的 SMTP 凭据。
- 不保留 OpenRouter 作为定时任务的必需依赖。
- 不改变现有信息来源的业务范围、排序权重或报告栏目。
- 不新增日报管理页面或其他用户界面。

## 架构

自动化分为三个边界清晰的部分：

1. Python CLI 采集候选内容。它读取 `config/sources.yml`，抓取现有来源，执行排序和历史去重，然后输出结构化 JSON，不调用 OpenRouter，也不发送邮件。
2. Codex 定时任务生成报告。它读取候选 JSON，根据固定编辑要求生成中文内容，同时产出用于仓库归档的 Markdown 和用于 Gmail 的 HTML 正文。
3. Gmail 插件发送邮件。它使用已连接的 Gmail 账号发信；发送成功后，任务将 Markdown 报告提交并推送到远程仓库。

Codex 定时任务在本地项目中运行。电脑必须保持开机，Codex App 必须在任务执行时运行，网络和 Gmail 插件连接必须可用。

## 数据流

每次运行按以下顺序执行：

1. 使用 `Asia/Shanghai` 计算本次报告日期。
2. 在 Gmail 已发送邮件中查询主题 `AI 开发者日报 - YYYY-MM-DD`。
3. 如果当天同主题邮件已经发送给目标收件人，停止本次发送并在任务结果中说明跳过原因。
4. 同步远程 `main`，避免基于过期报告历史执行去重。
5. 运行候选内容导出命令，得到条目、来源警告和排序结果。
6. Codex 按现有栏目生成中文摘要、推荐理由、行动建议和详细说明。
7. 校验报告日期、收件人、链接、栏目和正文非空。
8. 通过 Gmail 插件发送 HTML 邮件。
9. 将 Markdown 保存为 `reports/YYYY-MM-DD.md`，仅提交该报告和本次任务产生的必要文件，并推送到远程 `main`。
10. 在 Codex Scheduled 结果中记录发信和归档状态。

## 报告格式

邮件主题固定为 `AI 开发者日报 - YYYY-MM-DD`，日期按北京时间计算。

正文继续包含：

- 今日摘要
- 今日必看
- GitHub 热门项目
- 模型与数据集
- 论文与代码
- AI 开发者资讯
- Skills / Agents / 工具动态
- 今日行动建议
- 信息源警告（仅在存在警告时显示）

每个条目保留来源和原始链接，并提供中文介绍、价值判断、行动建议和适用场景。Codex 不得编造项目能力；信息不足时应明确使用原始描述或省略无法确认的判断。

## Gmail 发送规则

- 发件账号：`rockyyang951225@gmail.com`。
- 收件人：`rockyyang951225@gmail.com`、`zoeyli1997@gmail.com`。
- 用户已明确授权该定时任务向上述两个地址自动发送日报。
- 发送前必须执行同日主题查重，保证重复运行不会重复发信。
- 不使用草稿作为正常自动化步骤。
- Gmail 插件未连接、授权失效或发送失败时，不改用其他账号或 SMTP；任务应失败并报告原因。

## Git 与归档

- 报告保存到 `reports/YYYY-MM-DD.md`。
- 自动化只能暂存并提交本次生成的报告及明确属于该次运行的文件，不得提交工作区中的其他未跟踪或未提交内容。
- 提交信息使用 `chore: archive daily report`。
- 推送前同步远程分支。无法安全快进或变基时停止推送，并在 Scheduled 结果中报告冲突，不覆盖远程历史。
- 邮件发送成功但归档失败时，不再次发送邮件；后续运行通过 Gmail 查重识别已发送状态。

## 旧流水线处理

移除 `.github/workflows/daily-report.yml` 的定时 `schedule` 触发，保留 `workflow_dispatch` 作为人工备用入口。旧流水线不再是常规定时入口，以免与 Codex 任务重复发送。

手动备用入口可以继续生成基础版报告，但必须在文档中标明它仍可能依赖当前 GitHub Secrets 和 OpenRouter 配置。Codex 定时任务不调用该流水线。

## 失败处理

- 采集失败：保留各来源的 warning；若没有任何候选条目，则不发送空邮件。
- Codex 生成失败：不发送未完成正文，并在 Scheduled 中报告。
- Gmail 查重失败：为避免重复邮件，本次不发送并报告检查失败。
- Gmail 发送失败：不提交“已发送”状态；保留本地报告供排查。
- Git 推送失败：邮件不重发，Scheduled 中同时标记“邮件已发送、归档失败”。
- 任务未运行：由 Codex Scheduled 显示缺失或失败记录；本机开机和 Codex App 运行是外部前提。

## 测试与验收

代码验证包括：

- 候选导出命令在没有 OpenRouter Token 和 SMTP 配置时可以运行。
- 候选 JSON 包含排序后的条目、来源警告和北京时间报告日期。
- 现有采集、排序、历史去重和渲染测试继续通过。
- GitHub Actions 工作流不再包含定时 `schedule`，但保留手动触发。

上线验收包括：

- 手动运行一次完整 Codex 任务。
- 两个收件地址都收到同一封 HTML 日报。
- 发件账号、主题日期和正文日期正确。
- `reports/YYYY-MM-DD.md` 已推送到远程 `main`。
- 同一天再次运行时检测到已发送邮件并跳过发送。
- Codex Scheduled 中能看到成功、跳过或失败的明确结果。

## 定时任务配置

- 类型：独立 Codex 定时任务。
- 工作目录：`/Users/rockyyang/Wrokspace/每日推送/github-daily-report`。
- 执行环境：本地项目。
- 时区：`Asia/Shanghai`。
- 频率：每周一、周三 07:00。
- 状态：首次完整验收通过后设为启用。

