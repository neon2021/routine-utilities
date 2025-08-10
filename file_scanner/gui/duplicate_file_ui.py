import streamlit as st
import pandas as pd
import psycopg2
from global_config.logger_config import logger
from global_config.config import yaml_config_boxed


# 数据库连接参数
DB_CONFIG = {
    "host": yaml_config_boxed.gui.postgres.host,
    "port": 5432,
    "dbname": yaml_config_boxed.gui.postgres.dbname,
    "user": yaml_config_boxed.gui.postgres.user,
    "password": yaml_config_boxed.gui.postgres.password
}

# 三个 SQL 查询
SQL_DUPLICATE_FILES = """
SELECT * FROM file_inventory fi
WHERE fi.deleted = 0
  AND EXISTS (
      SELECT 1 FROM file_inventory f
      WHERE f.deleted = 0
        AND f.md5 = fi.md5
        AND f.path != fi.path
  )
ORDER BY size DESC;
"""

SQL_ALL_SUM_SIZE = """
SELECT SUM(size) AS all_sum_size
FROM file_inventory fi
WHERE fi.deleted = 0
  AND EXISTS (
      SELECT 1 FROM file_inventory f
      WHERE f.deleted = 0
        AND f.md5 = fi.md5
        AND f.path != fi.path
  );
"""

SQL_DISTINCTIVE_SUM_SIZE = """
SELECT SUM(size) AS distinctive_sum_size FROM (
  SELECT DISTINCT fi.md5, fi.size
  FROM file_inventory fi
  WHERE fi.deleted = 0
    AND EXISTS (
        SELECT 1 FROM file_inventory f
        WHERE f.deleted = 0
          AND f.md5 = fi.md5
          AND f.path != fi.path
    )
) t;
"""

# 页面标题
st.title("📂 重复文件分析报表")

# 连接数据库并查询
@st.cache_data(ttl=300)
def run_queries():
    conn = psycopg2.connect(**DB_CONFIG)
    df_duplicates = pd.read_sql(SQL_DUPLICATE_FILES, conn)
    sum_all = pd.read_sql(SQL_ALL_SUM_SIZE, conn)
    sum_distinct = pd.read_sql(SQL_DISTINCTIVE_SUM_SIZE, conn)
    conn.close()
    return df_duplicates, sum_all.iloc[0, 0], sum_distinct.iloc[0, 0]

# 执行查询
with st.spinner("正在加载数据..."):
    df_duplicates, all_sum, distinct_sum = run_queries()

# 显示统计信息
st.subheader("📊 重复文件大小统计")
st.metric(label="所有重复文件大小总和", value=f"{all_sum / (1024**3):.2f} GB")
st.metric(label="去重后的大小总和", value=f"{distinct_sum / (1024**3):.2f} GB")
st.metric(label="可节省空间", value=f"{(all_sum - distinct_sum) / (1024**3):.2f} GB")

# 展示重复文件列表
# st.subheader("📁 重复文件列表")
# st.dataframe(df_duplicates, use_container_width=True)

# pd.set_option("styler.render.max_elements", 10_000_000)  # 或更大

# 高亮重复文件：同一 md5 分组，第一个文件为正常颜色，其余为浅红色背景
def highlight_duplicates(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for md5, group in df.groupby('md5'):
        if len(group) > 1:
            for i, idx in enumerate(group.index):
                if i > 0:  # 除了第一个，其余设置浅红色背景
                    styles.loc[idx, :] = 'background-color: #ffe6e6'
    return styles

# 重新设置索引顺序（防止混乱）
df_duplicates_sorted = df_duplicates.sort_values(by=['size', 'md5', 'path'],ascending=[False,True,True])

# st.subheader("📁 重复文件列表（相同md5文件高亮显示）")
# st.dataframe(
#     df_duplicates_sorted.style.apply(highlight_duplicates, axis=None),
#     use_container_width=True
# )

MAX_ROWS = 500
df_show = df_duplicates_sorted.head(MAX_ROWS)

st.subheader(f"📁 重复文件列表（前 {MAX_ROWS} 条，高亮显示）")
st.dataframe(
    df_show.style.apply(highlight_duplicates, axis=None),
    use_container_width=True
)

# 允许下载完整结果（未加颜色）
st.download_button(
    label="📥 下载完整重复文件列表 CSV",
    data=df_duplicates_sorted.to_csv(index=False),
    file_name="duplicate_files.csv",
    mime="text/csv"
)
