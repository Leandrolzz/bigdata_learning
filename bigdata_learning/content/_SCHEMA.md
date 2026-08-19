# 学习内容 JSON 规范（_SCHEMA.md）

所有学习内容存放在 `content/` 目录，每个阶段一个 JSON 文件，文件名 = 阶段 ID（如 `s02_sql.json`）。
参考模板：`content/s00_intro.json`、`content/s01_python.json`（必须先用 `read` 工具阅读！）。

## 一、阶段（stage）字段

```json
{
  "stage_id": "s02_sql",
  "title": "阶段 2：SQL 从入门到精通",
  "subtitle": "大数据分析的第一语言",
  "emoji": "🗄️",
  "estimated_days": 12,
  "learning_goal": "掌握 SQL 查询、聚合、连接、窗口函数与优化思维。",
  "chapters": [ ... ]
}
```

## 二、章节（chapter）字段

```json
{
  "chapter_id": "s02c01",
  "title": "2.1 SELECT 基础查询",
  "goal": "学会 SELECT / WHERE / ORDER BY / LIMIT",
  "plan_days": 2,
  "plan_breakdown": { "theory_min": 40, "tasks_min": 50, "hands_on_min": 20, "review_min": 10 },
  "theory": [ ... ],
  "hands_on": "在命令行或 SQLite 中执行 ... 动手任务描述（markdown）",
  "tasks": [ ... ]
}
```

- `plan_days`：本章占用几天（全课程约 120 天）。
- `plan_breakdown`：每天 4 部分分钟数，合计 ≈ 120 分钟。
- `theory`：知识块数组，每个块一个对象：

| type | 说明 | 字段 |
|---|---|---|
| `text` | 正文（markdown） | content |
| `code` | 代码/示例块 | content（代码文本）、lang、caption（可选标题） |
| `tip` | 小提示（黄色框） | content |
| `warning` | 注意/易错（红色框） | content |
| `enterprise` | 企业视角（紫色框） | content |

每章理论要求：≥ 2 个 text 块、≥ 1 个 code 块、≥ 1 个 enterprise 块。

## 三、任务（task）字段

公共字段：`task_id`（全局唯一，如 `s02c01t01`）、`title`、`type`、`difficulty`（1~5）、`question`（markdown）、`analysis`（**标准解题思路**，分步骤讲解，必须详细）、`enterprise_tip`（可选，企业实战提示）、`hint`（可选，错误提示）。

### 3.1 choice（单选）
```json
{
  "task_id": "s02c01t01", "type": "choice", "difficulty": 2,
  "title": "选出正确的查询子句",
  "question": "以下哪个子句用于**过滤行**？",
  "options": [
    {"text": "SELECT", "correct": false, "explain": "SELECT 用于选择列，不是过滤行。"},
    {"text": "WHERE", "correct": true, "explain": "WHERE 在分组前过滤行，是正确答案。"},
    {"text": "GROUP BY", "correct": false, "explain": "GROUP BY 用于分组，不是过滤。"}
  ],
  "analysis": "**标准解题思路**\n1. ..."
}
```
要求：恰好 1 个 correct=true；每个选项必须写 explain（错误原因讲解）。

### 3.2 multi（多选）
同上，但 **至少 2 个** correct=true。

### 3.3 fill（填空）
```json
{
  "task_id": "s02c01t02", "type": "fill", "difficulty": 1,
  "title": "填空：去重关键字",
  "question": "SQL 中用于对查询结果去重的关键字是 ______。",
  "answer": ["DISTINCT", "distinct"],
  "hint": "三个字母开头，和 SELECT 搭配使用。",
  "analysis": "..."
}
```
`answer` 是**可接受答案数组**（≥2 个，含大小写变体；比对时忽略大小写与首尾空白）。

### 3.4 order（步骤排序）
```json
{
  "task_id": "s02c01t03", "type": "order", "difficulty": 3,
  "title": "排列 SQL 执行顺序",
  "question": "把 SQL 语句的执行顺序拖成正确顺序。",
  "steps": ["FROM/JOIN", "WHERE", "GROUP BY", "HAVING", "SELECT", "ORDER BY", "LIMIT"],
  "correct_order": [0, 1, 2, 3, 4, 5, 6],
  "order_explain": "SQL 先确定数据来源（FROM），再逐层过滤……",
  "analysis": "..."
}
```
`correct_order` 是 `steps` 索引的一个排列（如 `[0,1,2,3]` 表示按 steps 原顺序）。

### 3.5 sql（写 SQL，自动运行比对结果）
```json
{
  "task_id": "s02c01t04", "type": "sql", "difficulty": 2,
  "title": "查询男性用户",
  "question": "从 users 表中查出所有性别为 'M' 的用户姓名和年龄，按年龄降序排列。",
  "setup": "CREATE TABLE users (id INTEGER, name TEXT, age INTEGER, gender TEXT);\nINSERT INTO users VALUES (1,'张三',25,'M'),(2,'李四',30,'F'),(3,'王五',22,'M');",
  "expected_sql": "SELECT name, age FROM users WHERE gender='M' ORDER BY age DESC;",
  "analysis": "**标准解题思路**\n1. 确定表：FROM users ...",
  "enterprise_tip": "企业里这类查询每天跑在数亿行的大表上，必须注意加分区过滤。"
}
```

**SQL 任务的硬性约束（非常重要）：**
- 判定方式：把用户 SQL 在**内存 SQLite** 中执行，结果集与 `expected_sql` 的结果集比对（行集合 + 行数）。
- 只能使用 SQLite 支持的语法：SELECT/WHERE/GROUP BY/HAVING/ORDER BY/LIMIT/JOIN/子查询/UNION/CASE/聚合函数/窗口函数（ROW_NUMBER、RANK、DENSE_RANK、SUM() OVER、LAG/LEAD 等均可）。
- **禁止** Hive/Spark 特有语法：LATERAL VIEW、SORT BY、DISTRIBUTE BY、CLUSTER BY、`\\` 转义、日期函数 `from_unixtime`/`date_add` 等。
- 字符串函数只能用：substr、instr、length、replace、lower、upper、trim、printf。
- 日期一律存 TEXT（如 '2024-01-05'），日期计算用 `date('2024-01-05','+1 day')` 或 julianday 差值。
- 无 BOOLEAN 类型，用 0/1 表示；无 DATE/DATETIME 类型。
- `expected_sql` 结果必须**确定**（必须 ORDER BY，否则行序随机）。
- setup 的 INSERT 用 VALUES 多行简写。表名/字段名尽量贴近大数据场景（订单、用户、日志、流量等）。

### 3.6 python（写 Python 代码，自动运行比对 stdout）
```json
{
  "task_id": "s01c01t01", "type": "python", "difficulty": 1,
  "title": "输出两行内容",
  "question": "用 print() 输出两行：第一行 `Hello Big Data`，第二行 `I will be a data engineer`。",
  "code_context": "# 在这里编写代码\n# 例如：print('Hello Big Data')\n",
  "expected_output": "Hello Big Data\nI will be a data engineer",
  "reference": "print('Hello Big Data')\nprint('I will be a data engineer')",
  "analysis": "**标准解题思路**\n1. ...",
  "enterprise_tip": "..."
}
```

**Python 任务的硬性约束（非常重要）：**
- 用户代码在本机 Python 中 `python -c 代码` 运行，**只能使用标准库**。**严禁要求 pyspark / pandas / numpy / flink 等第三方库**（用户机器不一定装了）——涉及 Spark/Flink/Hadoop 概念时，用**纯 Python 模拟**（如用列表+字典模拟 map/reduce、用 dict 模拟聚合、用队列模拟流式窗口）。
- 运行工作目录是系统临时目录；代码必须自包含（需要数据就先用代码创建文件）。
- **禁止 input()**（会超时）。禁止 sleep、无限循环。
- `expected_output` 必须与参考答案 `reference` 的真实运行输出一致（比对时忽略每行首尾空白和末尾换行）。JSON 中换行写作 `\n`。
- `reference` 必填（标准答案代码，校验脚本会运行它核对 expected_output）。
- 代码里不要出现中文引号；字符串用单引号。

## 四、质量要求（每章）

1. 理论循序渐进：先概念 → 再语法 → 再例子 → 再易错点/企业视角。
2. 每章 2~3 个任务，类型尽量多样化（章节里至少包含 1 个"动手写"类任务：sql 或 python）。
3. 每个任务必须有详细 `analysis`（标准解题思路，分步骤，含为什么）。
4. `hands_on` 每章必填：给学习者布置一个真实的动手练习（在本地命令行/编辑器完成）。
5. 内容用简体中文；markdown 支持：`**加粗**`、`行内代码`、```代码块```、`### 小标题`、`- 列表`、`| 表格 |`（表格必须首尾有 |）。
6. JSON 必须是合法 JSON：UTF-8、无注释、无尾逗号、字符串转义正确。
7. 学习目标：让学习者"能看懂 → 能动手 → 能讲出来 → 能面试"。

## 五、企业视角要求（贯穿全部）

每个阶段、每章都要强调：这个概念在企业大数据平台中**为什么存在、怎么用、常见坑、面试怎么问**。尤其 SQL/Hive/Spark/Flink 阶段，尽量把任务场景设计成电商、日志、订单、流量等真实业务。

## 六、速记卡（章节巩固，v1.1 新增）

每个章节对象可包含两个巩固字段（**尽量每个章节都加**）：

```json
"qa": [
  {"q": "HDFS 默认副本数是几？", "a": "3。写文件时默认存储 3 份副本……"}
],
"glossary": [
  {"term": "NameNode", "desc": "HDFS 主节点，负责管理文件系统的元数据。"}
]
```

- `qa`：本章「常见问题」，3~5 条，问法贴近面试/易错点，答案要完整、能直接背诵。
- `glossary`：本章「重点词汇/命令/函数」，4~8 条，term 是术语、命令、函数或语法名，desc 一句话解释（含用途）。
- 平台在章节底部渲染为「📌 本章速记卡」手风琴，供通关后复习巩固。

## 六·五、知识点清单与出题密度（v1.2 新增，重要）

1. **知识点清单 `kps`**：每个章节必须加 `"kps": ["知识点1", "知识点2", ...]`，按教材顺序枚举本章全部知识点（5~10 个），平台会在章节顶部渲染成清单，保证「不跳过知识点」。
2. **出题密度与知识点一一对应**：章节任务数 = 知识点数量（建议 6~9 题/章，知识多的章节可以 10+），**每个知识点至少对应 1 道题**，不能跳过任何知识点。新增任务的 task_id 接续（如 s01c01t06）。
3. **教材式推进**：章节内部理论也要按知识点分段讲解，每个语法/机制/命令给：定义 → 示例代码 → 易错点/面试点，并且**该知识点必须配套题目**（choice/fill/order/sql/python 均可）。
4. **Linux/命令类章节特别要求**：常用命令要「逐个出题」（如 ls、cat、cp、mv、rm、tail、head、grep、sed、awk、sort、uniq、wc、chmod、crontab 等，每个命令至少 1 题考用法/参数）。
5. **底层原理要求（v1.3）**：每个阶段末尾追加「XX 底层原理进阶」章节（chapter_id 接续、plan_days 2、estimated_days 同步 +2），讲解机制级原理（如 HDFS 管道复制与 fsimage/edits、MapReduce Shuffle、Spark 统一内存与调度、Flink 状态后端与 Barrier 对齐、Kafka 零拷贝与 ISR、SQL 执行计划与 B+ 树、Python GIL 与哈希表、数仓拉链表与 UV 去重原理等），每个原理知识点必须配题。现有章节的 kps 若出现理论中有但无题的原理知识点，也要补题。
6. **第三方库题目**：python 任务若需要 pandas/numpy 等第三方库，加 `"requires": ["pandas"]` 字段——平台会自动检测环境，未安装时给出 `pip install` 提示；装有该库的用户可真实运行。其余 python 任务仍然必须纯标准库。

## 七、内容补丁工具（扩充内容时使用）

不直接手改大 JSON，使用补丁工具：

```
python tools/content_tools.py apply 补丁1.json 补丁2.json ...
```

补丁格式（可组合 `patches` / `new_chapters` / `stage_fields`）：

```json
{
  "file": "s01_python",
  "stage_fields": {"estimated_days": 18},
  "patches": [
    {
      "chapter_id": "s01c01",
      "add_tasks": [ {任务对象，规范同第三节} ],
      "qa": [ {"q": "...", "a": "..."} ],
      "glossary": [ {"term": "...", "desc": "..."} ]
    }
  ],
  "new_chapters": [ {完整章节对象，规范同第二节} ]
}
```

新增任务的 task_id 必须全局唯一（如 s01c01t04、s01c01t05……接续已有编号）；新增章节的 chapter_id 接续（如 s01c08），每章 2~4 个任务 + qa + glossary + hands_on + plan_days + plan_breakdown。

## 八、面试宝典（content/interview.json）

```json
{
  "title": "大数据面试宝典",
  "categories": [
    {
      "id": "iv_s01",
      "stage_id": "s01_python",
      "emoji": "🐍",
      "title": "Python 大数据基础",
      "items": [
        {"q": "Python 里列表和元组的区别？", "a": "列表可变、元组不可变……", "followup": "追问：那 set 呢？"}
      ]
    }
  ]
}
```
每阶段 8~10 题，问法 = 真实面试题，答案 = 结构化完整回答（先结论后展开，可背诵）。followup 为可选的面试官追问。
