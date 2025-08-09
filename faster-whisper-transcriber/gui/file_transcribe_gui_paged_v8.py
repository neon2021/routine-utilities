import os
import sys
import yaml
import vlc
import psycopg2
import datetime
import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

from global_config.config import yaml_config_boxed
from global_config.logger_config import logger


# ================= 统一分页组件 =================
# ================= 改进后的统一分页组件 =================
# ================= 修复后的统一分页组件（不会消失） =================
# ================= 最终修复后的统一分页组件（v4，无报错） =================
# ================= v8：最终稳定版分页组件（不会消失） =================
import streamlit as st

def pagination_component(total_records, key_prefix="pagination", default_page_size=20):
    page_key = f"{key_prefix}_page_number"
    size_key = f"{key_prefix}_page_size"

    # 初始化状态
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    if size_key not in st.session_state:
        st.session_state[size_key] = default_page_size

    # 计算总页数
    page_size = st.session_state[size_key]
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = total_pages

    # 分页组件固定位置
    pagination_placeholder = st.empty()
    with pagination_placeholder.container():
        cols_top = st.columns([1,1])
        # 分页大小
        page_size_option = cols_top[0].selectbox(
            "每页数量",
            [10, 20, 50, 100],
            index=[10,20,50,100].index(min(st.session_state[size_key],100))
            if st.session_state[size_key] in [10,20,50,100] else 1,
            key=f"{key_prefix}_page_size_option"
        )
        page_size_input = cols_top[1].number_input(
            "自定义每页数量",
            min_value=1,
            value=page_size_option,
            key=f"{key_prefix}_page_size_input"
        )
        st.session_state[size_key] = page_size_input
        page_size = page_size_input
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        if st.session_state[page_key] > total_pages:
            st.session_state[page_key] = total_pages

        st.write(f"总记录数：{total_records}，总页数：{total_pages}")

        # 翻页按钮
        cols = st.columns([1,1,2])
        if cols[0].button("上一页", key=f"{key_prefix}_prev") and st.session_state[page_key] > 1:
            st.session_state[page_key] -= 1
            st.experimental_rerun()
        if cols[1].button("下一页", key=f"{key_prefix}_next") and st.session_state[page_key] < total_pages:
            st.session_state[page_key] += 1
            st.experimental_rerun()

        # 跳转页码
        st.session_state[page_key] = cols[2].number_input(
            "跳转页码",
            min_value=1,
            max_value=total_pages,
            value=st.session_state[page_key],
            key=f"{key_prefix}_page_number_input"
        )

        st.write(f"当前第 {st.session_state[page_key]}/{total_pages} 页")

    return st.session_state[page_key], st.session_state[size_key]

# 使用示例
# page, size = pagination_component(total_records=len(result_df or []))
# start, end = (page-1)*size, (page-1)*size+size
# st.dataframe(result_df[start:end] if result_df is not None else [])

# ========== 配置 ==========
DB_CONFIGS = {
    "Postgres": yaml_config_boxed.gui.postgres.db_conn,
    "Ubuntu_Postgres": yaml_config_boxed.gui.ubuntu_postgres.db_conn
}

logger.name=os.path.basename(__file__)
def run_query(db_key, sql, params=None):
    cfg = DB_CONFIGS[db_key]
    conn = psycopg2.connect(cfg)
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df

def run_scalar(db_key, sql):
    cfg = DB_CONFIGS[db_key]
    conn = psycopg2.connect(cfg)
    cur = conn.cursor()
    cur.execute(sql)
    val = cur.fetchone()[0]
    cur.close()
    conn.close()
    return val

# ---- 默认值（你可以按需改）----
DEFAULTS = {
    "mime_selected": "",
    "size_min": 0,
    "size_max": 1000*1000*1000*1000,
    "path_keyword": "",
    "md5_value": "",
    "date_start": None,   # 若你的 streamlit 版本不支持 None，可改成 datetime.date(2025,1,1)
    "date_end": None,
}

# 首次运行时初始化
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# 若上一轮点击了“清除搜索条件”，则先重置，再清标志
if st.session_state.get("_do_clear_filters", False):
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.session_state["_do_clear_filters"] = False



st.title("File Inventory Explorer")

# ========== 数据源多选 ==========
st.subheader("选择数据源")
selected_dbs = []
col1, col2 = st.columns(2)
with col1:
    if st.checkbox("Postgres"):
        selected_dbs.append("Postgres")
with col2:
    if st.checkbox("Ubuntu_Postgres"):
        selected_dbs.append("Ubuntu_Postgres")

if not selected_dbs:
    st.warning("请至少选择一个数据源进行查询。")
    st.stop()

# ========== 文件类型统计 ==========
st.subheader("文件类型统计")

refresh_col1, refresh_col2 = st.columns([1, 3])
refresh_clicked = refresh_col1.button("刷新")

for db in selected_dbs:
    st.markdown(f"**数据源：{db}**")
    if refresh_clicked:
        # 获取最大扫描时间
        last_update = run_scalar(db, "SELECT max(scanned_at) FROM file_inventory WHERE deleted=0;")
        if isinstance(last_update, datetime):
            refresh_col2.write(f"**数据源：{db}** 最后扫描时间为：{last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            refresh_col2.write(f"**数据源：{db}** 最后扫描时间为：无记录")

    sql_mime_summary = """
    SELECT fi.mime_type,
           COUNT(*) AS cnt,
           SUM(fi.size) AS sum_file_size,
           MIN(gmt_create) AS min_time,
           MAX(gmt_create) AS max_time,
           EXTRACT(EPOCH FROM MAX(gmt_create) - MIN(gmt_create)) AS seconds_difference,
           EXTRACT(EPOCH FROM MAX(gmt_create) - MIN(gmt_create)) / 60 AS minutes_difference,
           EXTRACT(EPOCH FROM MAX(gmt_create) - MIN(gmt_create)) / 3600 AS hours_difference
    FROM file_inventory fi
    WHERE fi.deleted = 0
    GROUP BY fi.mime_type
    ORDER BY cnt DESC;
    """
    df_summary = run_query(db, sql_mime_summary)
    st.dataframe(df_summary)

# 动态获取 mime_type 列表（合并去重）
mime_types_all = []
for db in selected_dbs:
    df = run_query(db, "SELECT DISTINCT mime_type FROM file_inventory WHERE deleted=0;")
    mime_types_all.extend(df["mime_type"].dropna().tolist())
mime_types_all = sorted(set(mime_types_all))

# ========== 详细文件查询 ==========
st.subheader("详细文件查询")

# 初始化 session state 用于清除条件
if "query_params" not in st.session_state:
    st.session_state.query_params = {
        "mime_selected": None,
        "size_min": None,
        "size_max": None,
        "path_keyword": None,
        "md5_value": None,
        "date_start": None,
        "date_end": None
    }

def clear_filters():
    
    # # 重置控件的值
    # st.session_state.mime_selected = ""
    # st.session_state.size_min = 0
    # st.session_state.size_max = 1000*1000*1000*1000
    # st.session_state.path_keyword = ""
    # st.session_state.md5_value = ""
    # st.session_state.date_start = None
    # st.session_state.date_end = None
    
    # # 清空 session_state
    # st.session_state.query_params = {
    #     "mime_selected": "",
    #     "size_min": 0,
    #     "size_max": 1000*1000*1000*1000,
    #     "path_keyword": "",
    #     "md5_value": "",
    #     "date_start": None,
    #     "date_end": None
    # }
    
    st.session_state["_do_clear_filters"] = True
    st.rerun()  # 新接口；如果版本旧，用 st.experimental_rerun()

# 查询条件
mime_selected = st.selectbox("选择 MIME Type", [""] + mime_types_all, key="mime_selected")
size_min = st.number_input("最小文件大小 (字节)", value=0, key="size_min")
size_max = st.number_input("最大文件大小 (字节)", value=0, key="size_max")
path_keyword = st.text_input("文件路径包含关键字", key="path_keyword")
md5_value = st.text_input("MD5 精确匹配", key="md5_value")
date_start = st.date_input("扫描时间起始", value=None, key="date_start")
date_end = st.date_input("扫描时间结束", value=None, key="date_end")
# 分页设置


# 按钮行
col_run, col_clear = st.columns(2)
run_clicked = col_run.button("执行查询")
if col_clear.button("清除搜索条件"):
    clear_filters()
    # st.experimental_rerun()

def get_sql_and_params():
    base_sql = "SELECT * FROM file_inventory fi WHERE fi.deleted=0"
    params = []

    if mime_selected:
        base_sql += " AND fi.mime_type = %s"
        params.append(mime_selected)
    if size_min:
        base_sql += " AND fi.size > %s"
        params.append(size_min)
    if size_max:
        base_sql += " AND fi.size < %s"
        params.append(size_max)
    if path_keyword:
        base_sql += " AND fi.path LIKE %s"
        params.append(f"%{path_keyword}%")
    if md5_value:
        base_sql += " AND fi.md5 = %s"
        params.append(md5_value)
    if date_start:
        base_sql += " AND fi.scanned_at > %s"
        params.append(date_start)
    if date_end:
        base_sql += " AND fi.scanned_at < %s"
        params.append(date_end)

    # base_sql += " ORDER BY id DESC LIMIT %s OFFSET %s"
    # params.append(page_size_input)
    # params.append((page_number - 1) * page_size_input)
    
    return base_sql, params


if run_clicked:
    for db in selected_dbs:
        # 获取总记录数
        sql_count = "SELECT COUNT(*) FROM file_inventory fi WHERE fi.deleted=0"
        df_count = run_query(db, sql_count)
        total_records = int(df_count.iloc[0, 0])

        # 统一分页组件
        page_number, page_size = pagination_component(total_records, key_prefix=db)

        offset = (page_number - 1) * page_size

        sql, params = get_sql_and_params()
        sql += " ORDER BY fi.scanned_at DESC, fi.id DESC LIMIT %s OFFSET %s"
        params.append(page_size)
        params.append(offset)

        df = run_query(db, sql, params=params)
        st.dataframe(df)