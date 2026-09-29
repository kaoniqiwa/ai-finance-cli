# 💰 记账小工具

一个用 **Python + Streamlit + SQLite** 做的本地记账 Web 应用,完全离线运行,数据存在本机 `finance.db` 文件里。

## ✨ 功能

- **➕ 添加账目**:在表单里填金额、分类、日期、备注
- **📋 查看列表**:按月份/类型/分类筛选,表格展示
- **✏️ 编辑账目**:输入 ID 弹出编辑表单
- **🗑 删除账目**:输入 ID,二次确认后删除
- **📊 分类统计**:支出/收入按分类聚合,柱状图 + 统计表

## 🗂 预设分类

| 类型 | 分类 |
|------|------|
| 支出 | 餐饮、交通、购物、娱乐、居住、其他 |
| 收入 | 工资、奖金、红包、其他收入 |
| 转账 | 信用卡还款、余额转账 |

> 改分类请直接编辑 `db.py` 里的 `PRESET_CATEGORIES` 列表,删 `finance.db` 重跑即可重建。

## 🚀 快速开始

需要 **Python 3.10+**。

```bash
# 1. 进入项目目录
cd /Users/panminxiang/Sites/Commonfiles/Projects/finance-cli

# 2. 创建虚拟环境(第一次)
python3 -m venv .venv
source .venv/bin/activate

# 3. 装依赖
pip install -r requirements.txt

# 4. 启动应用
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`,看到 3 个 tab 就成功了 🎉

## 🧱 项目结构

```
finance-cli/
├── app.py          # Streamlit 入口(UI 全在这)
├── db.py           # 数据库连接 + 建表 + 预置分类
├── helpers.py      # CRUD + 统计函数(纯函数,不依赖 Streamlit)
├── requirements.txt
├── .gitignore
├── README.md
├── a.md            # 原始需求文档
├── xmind/          # 原始脑图
└── finance.db      # 你的数据(自动生成,不入 git)
```

## 🖱 操作指南

### 添加账目
1. 切到 **「➕ 添加」** tab
2. 选类型(支出/收入/转账)
3. 选分类(下拉框会根据类型自动过滤)
4. 填金额(必须 > 0)、日期(默认今天)、备注(选填)
5. 点 **💾 保存** → 看到 ✓ 提示和气球动画就成功了

### 查看/编辑/删除
1. 切到 **「📋 列表」** tab
2. 顶部 3 个多选框筛月份/类型/分类
3. 要编辑或删除,看表格里的 **ID** 列,在底部 **「🛠 操作」** 区输入 ID
4. 点 **✏️ 编辑** → 弹出预填好的编辑表单,改完点保存
5. 点 **🗑 删除** → 弹出红色确认按钮,再点一次才真删

### 看统计
1. 切到 **「📊 统计」** tab
2. 顶部选 **支出 / 收入**
3. 多选月份(不选 = 全部)
4. 看到柱状图 + 统计表

## ⚠️ 常见问题(新手必读)

1. **Streamlit 每次交互都重新跑整个 `app.py` 脚本**
   所以"点击编辑后展开表单"这种状态必须用 `st.session_state` 存,不能靠普通 Python 变量。本项目里 `editing_id` 和 `confirming_delete_id` 就是这个用途。

2. **SQL 永远用 `?` 占位符,不能 f-string 拼值**
   `f"WHERE name = '{user_input}'"` 是 SQL 注入漏洞。本项目所有查询都是 `?` + `params=`,可以放心。

3. **写完数据库要 `invalidate_caches()`**
   不然列表页/统计页还显示旧数据。`helpers.py` 的查询都被 `cached_*` 包了一层,`app.py` 的 `invalidate_caches()` 在每次写后会被调,会清掉缓存。

4. **`st.number_input` 默认返回 `float`**
   金额用 `min_value=0.01` 防止负数或 0。

5. **日期在 DB 里是字符串,过滤要用 `strftime`**
   `WHERE date = '2026-07-08'` 只匹配那一天,不是整个月。本项目用 `strftime('%Y-%m', date) IN (...)` 配 `'2026-07'` 这种格式。

6. **`st.dataframe` 是只读的,没有内置编辑功能**
   要"表格里点编辑"必须自己用 `st.button` + `st.expander` 拼。本项目没用 `st.data_editor`,因为它对新手来说黑盒、报错信息不友好。

7. **端口被占用怎么办?**
   ```bash
   streamlit run app.py --server.port 8502
   ```

## 🔧 想改点东西?

| 想改什么 | 看哪里 |
|----------|--------|
| 加/改分类 | `db.py` 里的 `PRESET_CATEGORIES` 列表 |
| 加/改列 | `db.py` 的 SQL + `helpers.py` 的函数 |
| 改页面长什么样 | `app.py` 里的 `render_*_tab` 函数 |
| 改统计口径 | `helpers.py` 里的 `get_category_stats` |

## 🧪 怎么手动测试 db / helpers

```bash
.venv/bin/python db.py        # 验证 12 条预置分类
.venv/bin/python helpers.py   # 跑通 CRUD 流程,会自动插 3 条 + 改 1 条 + 删 1 条
```

## ⚙️ 数据库存放位置

`finance.db` 跟 `app.py` 在同一目录,已加进 `.gitignore`,不会污染版本控制。

**想重置数据?** 删掉 `finance.db` 即可,下次启动会自动重建。

## 📦 依赖

只有 2 个:
- `streamlit` — Web UI 框架
- `pandas` — 表格处理(Streamlit 显示用)

`sqlite3` 是 Python 标准库,不需要装。

## 🚧 已知限制

- 金额用 `REAL` 存储,理论上可能有浮点误差。生产环境建议改成 `INTEGER` 存"分"。
- 暂不支持多账本/多用户,所有数据混在一起。
- 暂不支持导入/导出(可以加,工作量大但不难)。
