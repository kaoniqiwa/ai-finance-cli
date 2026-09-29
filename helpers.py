"""业务层:所有 CRUD 和统计函数。

新手提示:
- 本模块是纯函数,不依赖 Streamlit,可以单独测试。
- 所有 SQL 一律用 ? 占位符,绝对不要用 f-string 拼值,防 SQL 注入。
- 返回值是 pandas DataFrame,方便 Streamlit 直接 st.dataframe() 显示。
"""

from typing import Any, Optional
import pandas as pd

from db import get_connection

# 业务常量(给下拉框 / 中文显示用)
TYPE_LABELS = {
    "expense": "支出",
    "income": "收入",
    "transfer": "转账",
}
TYPE_CHOICES = ["expense", "income", "transfer"]


# ---------------------------------------------------------------------------
# 分类相关
# ---------------------------------------------------------------------------

def get_categories(type: Optional[str] = None) -> pd.DataFrame:
    """取分类列表。type 为 None 时返回全部;否则按类型过滤。"""
    conn = get_connection()
    try:
        if type is None:
            df = pd.read_sql_query(
                "SELECT id, name, type FROM categories ORDER BY type, id",
                conn,
            )
        else:
            df = pd.read_sql_query(
                "SELECT id, name, type FROM categories WHERE type = ? ORDER BY id",
                conn,
                params=(type,),
            )
        return df
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 账目 CRUD
# ---------------------------------------------------------------------------

def add_transaction(
    type: str,
    amount: float,
    category_id: int,
    date: str,
    note: str = "",
) -> int:
    """添加一笔账目,返回新 id。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO transactions (type, amount, category_id, date, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (type, float(amount), int(category_id), date, note),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_transactions(
    months: Optional[list[str]] = None,
    types: Optional[list[str]] = None,
    category_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    """查账目,带可选筛选。

    参数:
        months       — 例 ['2026-07', '2026-06'],None 或 [] 表示不限
        types        — 例 ['expense', 'income'],None 或 [] 表示不限
        category_ids — 例 [1, 2, 3],None 或 [] 表示不限

    返回 DataFrame 列:id, date, type, type_label, category, category_id, amount, note
    按 date DESC, id DESC 排序。
    """
    where_parts: list[str] = []
    params: list[Any] = []

    if months:
        placeholders = ",".join("?" for _ in months)
        where_parts.append(f"strftime('%Y-%m', t.date) IN ({placeholders})")
        params.extend(months)
    if types:
        placeholders = ",".join("?" for _ in types)
        where_parts.append(f"t.type IN ({placeholders})")
        params.extend(types)
    if category_ids:
        placeholders = ",".join("?" for _ in category_ids)
        where_parts.append(f"t.category_id IN ({placeholders})")
        params.extend(category_ids)

    where_sql = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    sql = f"""
        SELECT t.id, t.date, t.type, c.name AS category, t.category_id,
               t.amount, t.note
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        {where_sql}
        ORDER BY t.date DESC, t.id DESC
    """

    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

    # 把 type 翻译成中文,放一列方便显示
    if not df.empty:
        df["type_label"] = df["type"].map(TYPE_LABELS).fillna(df["type"])
    else:
        df["type_label"] = pd.Series(dtype=str)

    return df


def update_transaction(id: int, **fields: Any) -> None:
    """改一笔账目。fields 允许的键:type, amount, category_id, date, note。"""
    allowed = {"type", "amount", "category_id", "date", "note"}
    sets: list[str] = []
    params: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            raise ValueError(f"不允许的字段: {key}")
        sets.append(f"{key} = ?")
        params.append(value)
    if not sets:
        return  # 啥也没改

    params.append(int(id))
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()


def delete_transaction(id: int) -> None:
    """按 id 删除一笔账目。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM transactions WHERE id = ?", (int(id),))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

def get_category_stats(
    type: str,
    months: Optional[list[str]] = None,
) -> pd.DataFrame:
    """按分类聚合统计。

    返回 DataFrame 列:category, total, count, percent
    按 total DESC 排序。
    """
    where_parts: list[str] = ["t.type = ?"]
    params: list[Any] = [type]

    if months:
        placeholders = ",".join("?" for _ in months)
        where_parts.append(f"strftime('%Y-%m', t.date) IN ({placeholders})")
        params.extend(months)

    where_sql = "WHERE " + " AND ".join(where_parts)

    # 用 INNER JOIN:这样分类如果没有交易就不会出现,统计里全是 0 的分类不显示
    sql = f"""
        SELECT c.name AS category,
               COALESCE(SUM(t.amount), 0) AS total,
               COUNT(t.id) AS count
        FROM categories c
        JOIN transactions t ON t.category_id = c.id
        {where_sql}
        GROUP BY c.id, c.name
        ORDER BY total DESC
    """

    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

    if df.empty:
        return df

    # 计算百分比
    grand_total = df["total"].sum()
    if grand_total > 0:
        df["percent"] = (df["total"] / grand_total * 100).round(1)
    else:
        df["percent"] = 0.0
    return df


# ---------------------------------------------------------------------------
# 手动测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 这个块只在直接 python helpers.py 时跑,被 import 时不会跑
    print("=== 测试 helpers ===\n")

    # 1. 查分类
    cats = get_categories()
    print(f"分类数: {len(cats)}")
    print(cats.head(3).to_string(index=False))
    print()

    # 2. 插 3 条
    id1 = add_transaction("expense", 50, 1, "2026-07-08", "午餐")
    id2 = add_transaction("expense", 8, 2, "2026-07-08", "地铁")
    id3 = add_transaction("income", 10000, 7, "2026-07-01", "7月工资")
    print(f"插入 3 条,id: {id1}, {id2}, {id3}\n")

    # 3. 列表
    df = list_transactions()
    print(f"总账目数: {len(df)}")
    print(df[["id", "date", "type_label", "category", "amount", "note"]].to_string(index=False))
    print()

    # 4. 改一条
    update_transaction(id1, amount=60, note="午餐(改)")
    df2 = list_transactions(months=["2026-07"], types=["expense"])
    print(f"改完后 id={id1} 的金额应该是 60:")
    print(df2[df2["id"] == id1][["id", "amount", "note"]].to_string(index=False))
    print()

    # 5. 统计
    stats = get_category_stats("expense", months=["2026-07"])
    print("支出统计:")
    print(stats.to_string(index=False))
    print()

    # 6. 删一条
    delete_transaction(id3)
    print(f"删除 id={id3} 后,总账目数: {len(list_transactions())}")
