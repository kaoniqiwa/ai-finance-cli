"""Streamlit 记账应用主入口。

新手提示:
- 整个文件被 Streamlit 反复执行,所有"会变"的状态都要放 st.session_state。
- @st.cache_data 让查询函数的结果缓存,避免每次都打数据库。
- 写完数据库后,务必 clear 缓存,否则列表页/统计页会显示旧数据。
"""

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from db import init_db
from helpers import (
    TYPE_CHOICES,
    TYPE_LABELS,
    add_transaction,
    delete_transaction,
    get_categories,
    get_category_stats,
    list_transactions,
    update_transaction,
)


# ---------------------------------------------------------------------------
# 启动初始化
# ---------------------------------------------------------------------------

st.set_page_config(page_title="记账小工具", page_icon="💰", layout="wide")

# 第一次启动时建表 + 写预置分类
init_db()


# ---------------------------------------------------------------------------
# session_state 初始化
# 新手提示:st.session_state 像一个 dict,在多次 rerun 之间保持值。
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    if "editing_id" not in st.session_state:
        st.session_state.editing_id = None
    if "confirming_delete_id" not in st.session_state:
        st.session_state.confirming_delete_id = None


init_session_state()


# ---------------------------------------------------------------------------
# 工具函数:失效缓存
# ---------------------------------------------------------------------------

def invalidate_caches() -> None:
    """写完数据库后调用,让列表/统计 tab 看到最新数据。"""
    cached_list_transactions.clear()
    cached_get_categories.clear()
    cached_get_category_stats.clear()


# ---------------------------------------------------------------------------
# 缓存包装:把 helpers 里的查询包一层 st.cache_data
# ---------------------------------------------------------------------------

@st.cache_data
def cached_list_transactions(
    months: Optional[tuple],
    types: Optional[tuple],
    category_ids: Optional[tuple],
) -> pd.DataFrame:
    """缓存 list_transactions 结果。

    新手提示:
    - Streamlit 不能直接缓存 list/dict,要用 tuple。
    - 写完数据库必须 clear_cache(),否则这里还是旧数据。
    """
    return list_transactions(
        months=list(months) if months else None,
        types=list(types) if types else None,
        category_ids=list(category_ids) if category_ids else None,
    )


@st.cache_data
def cached_get_categories(type: Optional[str] = None) -> pd.DataFrame:
    return get_categories(type)


@st.cache_data
def cached_get_category_stats(type: str, months_tuple: Optional[tuple]) -> pd.DataFrame:
    return get_category_stats(
        type=type,
        months=list(months_tuple) if months_tuple else None,
    )


# ---------------------------------------------------------------------------
# Tab 1: 添加账目
# ---------------------------------------------------------------------------

def render_add_tab() -> None:
    st.header("➕ 添加账目")

    with st.form("add_form", clear_on_submit=True):
        # 类型
        type_code = st.selectbox(
            "类型",
            options=TYPE_CHOICES,
            format_func=lambda x: TYPE_LABELS[x],
            key="add_type",
        )
        # 分类(按 type 过滤)
        cats_df = cached_get_categories(type_code)
        if cats_df.empty:
            st.error("没有可用的分类,请检查数据库初始化。")
            return
        category_name = st.selectbox(
            "分类",
            options=cats_df["name"].tolist(),
            key="add_category",
        )
        category_id = int(cats_df[cats_df["name"] == category_name].iloc[0]["id"])

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "金额(元)",
                min_value=0.01,
                step=1.0,
                format="%.2f",
                key="add_amount",
            )
        with col2:
            trans_date = st.date_input("日期", value=date.today(), key="add_date")

        note = st.text_input("备注", key="add_note", placeholder="选填")

        submitted = st.form_submit_button("💾 保存", use_container_width=True)

        if submitted:
            new_id = add_transaction(
                type=type_code,
                amount=amount,
                category_id=category_id,
                date=trans_date.isoformat(),
                note=note.strip(),
            )
            invalidate_caches()
            st.success(f"✓ 已保存!账目 id = {new_id}")
            st.balloons()


# ---------------------------------------------------------------------------
# Tab 2: 账目列表
# ---------------------------------------------------------------------------

def render_list_tab() -> None:
    st.header("📋 账目列表")

    # 顶部筛选条
    filter_cols = st.columns(3)
    with filter_cols[0]:
        # 月份选项:从所有交易里抽,去重
        all_df = cached_list_transactions(None, None, None)
        if not all_df.empty:
            all_df["month"] = pd.to_datetime(all_df["date"]).dt.strftime("%Y-%m")
            month_options = sorted(all_df["month"].unique().tolist(), reverse=True)
        else:
            month_options = []
        selected_months = st.multiselect("月份", options=month_options, key="filter_months")

    with filter_cols[1]:
        selected_types = st.multiselect(
            "类型",
            options=TYPE_CHOICES,
            format_func=lambda x: TYPE_LABELS[x],
            key="filter_types",
        )

    with filter_cols[2]:
        all_cats = cached_get_categories(None)
        cat_options = all_cats["name"].tolist()
        selected_cats = st.multiselect("分类", options=cat_options, key="filter_cats")

    # 计算分类 id 列表
    selected_cat_ids: list[int] = []
    if selected_cats:
        selected_cat_ids = all_cats[all_cats["name"].isin(selected_cats)]["id"].astype(int).tolist()

    # 查询
    df = cached_list_transactions(
        tuple(selected_months) if selected_months else None,
        tuple(selected_types) if selected_types else None,
        tuple(selected_cat_ids) if selected_cat_ids else None,
    )

    if df.empty:
        st.info("没有匹配的账目,试试在「添加」页记一笔 ✍️")
        return

    # 显示
    st.caption(f"共 {len(df)} 条,总金额 ¥{df['amount'].sum():.2f}")
    show_df = df[["id", "date", "type_label", "category", "amount", "note"]].rename(
        columns={"id": "ID", "date": "日期", "type_label": "类型",
                 "category": "分类", "amount": "金额", "note": "备注"}
    )
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    # ---- 操作区:输入 ID 编辑或删除 ----
    st.divider()
    st.subheader("🛠 操作")
    op_cols = st.columns([1, 2, 2, 5])
    with op_cols[0]:
        op_id = st.number_input(
            "账目 ID", min_value=1, step=1, value=1, key="op_id_input"
        )
    with op_cols[1]:
        if st.button("✏️ 编辑", use_container_width=True):
            # 检查 ID 是否存在
            if int(op_id) in df["id"].astype(int).tolist():
                st.session_state.editing_id = int(op_id)
                st.session_state.confirming_delete_id = None
                st.rerun()
            else:
                st.error(f"ID {int(op_id)} 不在当前筛选结果中")
    with op_cols[2]:
        if st.button("🗑 删除", use_container_width=True):
            if int(op_id) in df["id"].astype(int).tolist():
                st.session_state.confirming_delete_id = int(op_id)
                st.session_state.editing_id = None
                st.rerun()
            else:
                st.error(f"ID {int(op_id)} 不在当前筛选结果中")

    # ---- 删除二次确认 ----
    if st.session_state.confirming_delete_id is not None:
        cid = st.session_state.confirming_delete_id
        st.warning(f"⚠️ 再次点击下方红色按钮确认删除账目 #{cid}")
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button(f"🗑 确认删除 #{cid}", type="primary"):
                delete_transaction(cid)
                invalidate_caches()
                st.session_state.confirming_delete_id = None
                st.success(f"已删除账目 #{cid}")
                st.rerun()
        with c2:
            if st.button("取消"):
                st.session_state.confirming_delete_id = None
                st.rerun()

    # ---- 编辑表单 ----
    if st.session_state.editing_id is not None:
        render_edit_form(st.session_state.editing_id)


# ---------------------------------------------------------------------------
# 编辑表单
# ---------------------------------------------------------------------------

def render_edit_form(trans_id: int) -> None:
    """渲染编辑表单,放在一个 expander 里。"""
    # 从 DB 拿当前值(不经过缓存,确保最新)
    all_df = list_transactions()  # 拿到完整字段,包括 category_id
    row = all_df[all_df["id"] == trans_id]
    if row.empty:
        st.error(f"找不到 ID = {trans_id} 的账目,可能已被删除。")
        st.session_state.editing_id = None
        return
    current = row.iloc[0]

    with st.expander(f"✏️ 编辑账目 #{trans_id}", expanded=True):
        with st.form(f"edit_form_{trans_id}"):
            new_type = st.selectbox(
                "类型",
                options=TYPE_CHOICES,
                index=TYPE_CHOICES.index(current["type"]),
                format_func=lambda x: TYPE_LABELS[x],
                key=f"edit_type_{trans_id}",
            )
            cats_df = cached_get_categories(new_type)
            cat_names = cats_df["name"].tolist()
            current_cat_name = current["category"]
            # 如果当前分类不在新 type 列表里(比如把"信用卡还款"从转账改成支出),
            # 就回退到第一项
            if current_cat_name not in cat_names:
                current_cat_name = cat_names[0]
            new_cat_name = st.selectbox(
                "分类",
                options=cat_names,
                index=cat_names.index(current_cat_name),
                key=f"edit_cat_{trans_id}",
            )
            new_cat_id = int(cats_df[cats_df["name"] == new_cat_name].iloc[0]["id"])

            c1, c2 = st.columns(2)
            with c1:
                new_amount = st.number_input(
                    "金额",
                    min_value=0.01,
                    step=1.0,
                    format="%.2f",
                    value=float(current["amount"]),
                    key=f"edit_amount_{trans_id}",
                )
            with c2:
                new_date = st.date_input(
                    "日期",
                    value=date.fromisoformat(current["date"]),
                    key=f"edit_date_{trans_id}",
                )

            new_note = st.text_input(
                "备注",
                value=str(current["note"] or ""),
                key=f"edit_note_{trans_id}",
            )

            s1, s2 = st.columns(2)
            with s1:
                if st.form_submit_button("💾 保存修改", use_container_width=True, type="primary"):
                    update_transaction(
                        trans_id,
                        type=new_type,
                        amount=new_amount,
                        category_id=new_cat_id,
                        date=new_date.isoformat(),
                        note=new_note.strip(),
                    )
                    invalidate_caches()
                    st.session_state.editing_id = None
                    st.success(f"✓ 账目 #{trans_id} 已更新")
                    st.rerun()
            with s2:
                if st.form_submit_button("取消", use_container_width=True):
                    st.session_state.editing_id = None
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab 3: 分类统计
# ---------------------------------------------------------------------------

def render_stats_tab() -> None:
    st.header("📊 分类统计")

    # 类型选择
    stat_type = st.radio(
        "统计类型",
        options=["expense", "income"],
        format_func=lambda x: TYPE_LABELS[x],
        horizontal=True,
        key="stat_type",
    )

    # 月份筛选(与列表 tab 共用,也可以在这里改)
    all_df = cached_list_transactions(None, None, None)
    if not all_df.empty:
        all_df["month"] = pd.to_datetime(all_df["date"]).dt.strftime("%Y-%m")
        month_options = sorted(all_df["month"].unique().tolist(), reverse=True)
    else:
        month_options = []
    selected_months = st.multiselect(
        "月份(不选则统计全部)",
        options=month_options,
        key="stat_months",
    )

    # 查统计
    stats_df = cached_get_category_stats(
        stat_type,
        tuple(selected_months) if selected_months else None,
    )

    if stats_df.empty:
        st.info(f"暂无{TYPE_LABELS[stat_type]}数据,先在「添加」页记几笔吧 ✍️")
        return

    # 总计
    total = stats_df["total"].sum()
    count = stats_df["count"].sum()
    cols = st.columns(3)
    cols[0].metric("总金额", f"¥{total:,.2f}")
    cols[1].metric("总笔数", f"{count}")
    cols[2].metric("分类数", f"{len(stats_df)}")

    # 柱状图
    st.subheader("📈 柱状图")
    chart_df = stats_df.set_index("category")[["total"]]
    st.bar_chart(chart_df, height=400)

    # 统计表
    st.subheader("📋 详细数据")
    show_stats = stats_df.rename(
        columns={"category": "分类", "total": "金额", "count": "笔数", "percent": "占比(%)"}
    )
    st.dataframe(show_stats, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("💰 记账小工具")
    st.caption("Python + Streamlit + SQLite · 本机运行 · 数据存 finance.db")

    tab_add, tab_list, tab_stats = st.tabs(["➕ 添加", "📋 列表", "📊 统计"])

    with tab_add:
        render_add_tab()
    with tab_list:
        render_list_tab()
    with tab_stats:
        render_stats_tab()


if __name__ == "__main__":
    main()
