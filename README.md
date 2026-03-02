# BYXT 选课监控与自动选课

当前推荐使用 CSV 工作流脚本：

- `scripts/byxt_csv_flow.py`

## 功能概览

该脚本支持：

1. 首次运行时提示输入账号密码，并写入配置文件 `output/byxt_config.json`。
2. 自动抓取课程平台课程并导出 `output/all_courses.csv`（包含页面可见字段 + 原始字段展开）。
3. 用户从 `all_courses.csv` 复制目标课程行到 `output/targets.csv`，填写 `target_pool`（`对内`/`对外`）。
4. 程序按 `course_code + sequence` **精确匹配**，只监控目标课程。
5. 轮询期间若登录态掉线，自动重登并重试一次。
6. 每轮打印 `[WATCH]` 监控明细（课程代码、课序号、名称、容量/选量）。

## 安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pytest httpx pydantic
```

## 运行

```bash
.venv/bin/python scripts/byxt_csv_flow.py
```

### 首次运行

会提示输入：

- BYXT 学号/用户名
- BYXT 密码

并生成 `output/byxt_config.json`。

## 目标课程配置方式

1. 先运行一次脚本，得到 `output/all_courses.csv`。
2. 从 `all_courses.csv` 复制你要的课程行到 `output/targets.csv`。
3. 在 `targets.csv` 的 `target_pool` 列填写：
   - `对内`（或 `internal`）
   - `对外`（或 `external`）

程序会按 `course_code + sequence` 精确匹配课程。

## 配置文件说明（output/byxt_config.json）

常用字段：

- `execution_mode`: `READ_ONLY` / `DRY_RUN` / `ARMED`
- `poll_interval_seconds`: 轮询间隔（秒）
- `teaching_class_types`: 默认 `["XGKC", "TJKC"]`（会同时抓两类，减少漏课）
- `page_size`
- `max_pages`
- `all_courses_csv`
- `target_courses_csv`
- `stop_after_success`

## 掉线恢复

当接口返回非 JSON（常见于登录态过期跳转页）时，程序会识别为会话失效，自动重登并重试一次。

## 红线保障（不退选）

- 只允许调用白名单行为（登录/查询/选课/已选查询）。
- 明确拒绝退选相关端点（例如 `/elective/clazz/del`、`/elective/deselect`）。
- 提交前后执行已选集合一致性校验，确保已选课程不减少。

## 免责声明与使用条款

本项目仅用于合法合规前提下的学习研究与个人自动化实践。使用者必须自行确认并遵守学校/平台规则、服务协议及相关法律法规。

你需自行承担账号与数据安全责任（包括但不限于密码、Token、抓包记录、导出文件）。

项目作者与贡献者不对因违规使用、平台策略变化、网络/环境异常导致的账号问题、选课失败、数据偏差或其他损失承担责任。

若你不同意以上条款，请勿使用本项目。

## 测试

```bash
.venv/bin/python -m pytest -v tests
```
