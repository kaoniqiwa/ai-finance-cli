"""数据库层:建表、连接、预置分类。

新手提示:
- 本模块只关心"数据库长什么样",不关心页面。
- sqlite3 是 Python 自带的标准库,不需要 pip install。
- 第一次启动应用时会自动调用 init_db() 建表 + 写预置数据。
"""

import os
import sqlite3
from pathlib import Path

# 数据库文件路径:与 app.py 同目录下的 finance.db
DB_PATH = Path(__file__).parent / "finance.db"

# 预置分类:(type, name)
# type 取值: 'expense' 支出 | 'income' 收入 | 'transfer' 转账
PRESET_CATEGORIES = [
    # 6 个支出分类(对应 a.md 需求)
    ("expense", "餐饮"),
    ("expense", "交通"),
    ("expense", "购物"),
    ("expense", "娱乐"),
    ("expense", "居住"),
    ("expense", "其他"),
    # 4 个收入分类
    ("income", "工资"),
    ("income", "奖金"),
    ("income", "红包"),
    ("income", "其他收入"),
    # 2 个转账分类
    ("transfer", "信用卡还款"),
    ("transfer", "余额转账"),
]


def get_connection() -> sqlite3.Connection:
    """获取一个数据库连接。

    新手提示:
    - row_factory = sqlite3.Row 让查询结果可以像字典一样访问 row["name"]
    - PRAGMA foreign_keys = ON 启用外键约束(默认是关的)
    - check_same_thread = False 是为了兼容 Streamlit 的多线程
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化数据库:建表 + 写入预置分类(只在第一次或分类缺失时执行)。"""
    conn = get_connection()
    try:
        # categories 表:分类字典
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense','income','transfer'))
            )
            """
        )

        # transactions 表:账目流水
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT NOT NULL CHECK(type IN ('expense','income','transfer')),
                amount      REAL NOT NULL CHECK(amount > 0),
                category_id INTEGER NOT NULL,
                date        TEXT NOT NULL,
                note        TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
            """
        )
        # 索引:加速按日期和按 (类型+分类) 的查询
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(date)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trans_type_cat ON transactions(type, category_id)"
        )

        # 写入预置分类(已存在则跳过)
        # INSERT OR IGNORE 要求 name 唯一,但目前 name 没加 UNIQUE 约束,
        # 所以手动用 SELECT 判一下,避免重复插入同名分类
        for cat_type, cat_name in PRESET_CATEGORIES:
            cur = conn.execute(
                "SELECT 1 FROM categories WHERE name = ? AND type = ?",
                (cat_name, cat_type),
            )
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO categories (name, type) VALUES (?, ?)",
                    (cat_name, cat_type),
                )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # 直接跑这个文件可以手动初始化数据库,验证表结构
    print(f"DB 路径: {DB_PATH}")
    init_db()
    print("✓ init_db() 完成")

    # 打印表结构
    conn = get_connection()
    print("\n=== categories 表内容 ===")
    for row in conn.execute("SELECT * FROM categories ORDER BY type, id"):
        print(f"  {row['id']:>2}  {row['type']:<8}  {row['name']}")
    conn.close()
