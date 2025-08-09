import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from datetime import datetime

from global_config.logger_config import logger
from global_config.config import yaml_config_boxed

# PostgreSQL连接配置
conn_params = {
    "host": yaml_config_boxed.gui.postgres.host,
    "port": 5432,
    "dbname": yaml_config_boxed.gui.postgres.dbname,
    "user": yaml_config_boxed.gui.postgres.user,
    "password": yaml_config_boxed.gui.postgres.password
}

# 数据库连接
engine = create_engine(
    f"postgresql+psycopg2://{conn_params['user']}:{conn_params['password']}@{conn_params['host']}:{conn_params['port']}/{conn_params['dbname']}"
)

# SQL 查询语句
SQL_QUERY_DAILY = """
SELECT 
    DATE(fi.scanned_at) AS scan_date, 
    fi.deleted, 
    COUNT(*) AS cnt 
FROM file_inventory fi
WHERE fi.scanned_at >= NOW() - INTERVAL '3 days'
GROUP BY scan_date, fi.deleted
ORDER BY scan_date, fi.deleted
"""


SQL_QUERY_1 = """
SELECT fi.deleted, MAX(fi.scanned_at) AS max_scanned_at, COUNT(*) AS cnt 
FROM file_inventory fi 
GROUP BY fi.deleted
"""

SQL_QUERY_2 = """
SELECT fi.deleted, TO_CHAR(fi.scanned_at, 'yyyy-mm-dd HH24') AS ymdh_scanned_at, COUNT(*) AS cnt 
FROM file_inventory fi
WHERE fi.scanned_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY fi.deleted, TO_CHAR(fi.scanned_at, 'yyyy-mm-dd HH24')
ORDER BY ymdh_scanned_at
"""

# 初始化 Dash 应用
app = dash.Dash(__name__)
app.title = "PostgreSQL 实时柱状图"

# 页面布局
app.layout = html.Div([
    html.H1("PostgreSQL 实时数据可视化", style={'textAlign': 'center'}),

    html.Div(id='stat-panel', style={
        'fontSize': '18px',
        'padding': '12px',
        'whiteSpace': 'pre-line',
        'backgroundColor': '#f9f9f9',
        'border': '1px solid #ccc',
        'borderRadius': '8px',
        'marginBottom': '20px',
        'textAlign': 'left'
    }),


    dcc.Graph(id='bar-chart-1'),
    html.Hr(),
    dcc.Graph(id='bar-chart-2'),

    dcc.Interval(
        id='interval-component',
        interval=5 * 1000,  # 每5秒刷新
        n_intervals=0
    )
], style={'margin': '40px'})

# 回调函数：刷新图表和统计面板
@app.callback(
    Output('bar-chart-1', 'figure'),
    Output('bar-chart-2', 'figure'),
    Output('stat-panel', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    try:
        # 查询数据
        df1 = pd.read_sql(SQL_QUERY_1, engine)
        df2 = pd.read_sql(SQL_QUERY_2, engine)

        # 柱状图1：deleted 分类的总量
        fig1 = px.bar(
            df1.sort_values('deleted'),
            x='deleted',
            y='cnt',
            color='deleted',
            title='各 Deleted 状态的文件数量'
        )
        fig1.update_layout(xaxis_title='deleted', yaxis_title='文件数')

        # 柱状图2：按小时分组
        fig2 = px.bar(
            df2.sort_values('ymdh_scanned_at'),
            x='ymdh_scanned_at',
            y='cnt',
            color='deleted',
            barmode='group',
            title='近 24 小时各 Deleted 状态每小时扫描数量'
        )
        fig2.update_layout(xaxis_title='扫描时间（小时）', yaxis_title='文件数')

        # 更新顶部统计区块
        # 拆分 deleted=0 和 deleted=1 的总数
        # 查询按天统计数据
        df_day = pd.read_sql(SQL_QUERY_DAILY, engine)

        # 按天和 deleted 分组
        grouped = df_day.groupby(['scan_date', 'deleted'])['cnt'].sum().unstack(fill_value=0)

        # 构建展示字符串
        daily_stat_lines = []
        for day in grouped.index:
            cnt_0 = grouped.loc[day].get(0, 0)
            cnt_1 = grouped.loc[day].get(1, 0)
            total = cnt_0 + cnt_1
            daily_stat_lines.append(
                f"- {day}: 总计 {total:,}（deleted=0: {cnt_0:,}，deleted=1: {cnt_1:,}）"
            )

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stat_text = f"当前时间：{now_str} ｜ 近几天文件总数（按 deleted 分类）：\n" + "\n".join(daily_stat_lines)

        return fig1, fig2, stat_text

    except Exception as e:
        logger.exception("刷新出错：")
        return dash.no_update, dash.no_update, dash.no_update

# 启动服务器
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True, port=8050)