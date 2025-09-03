import os
import sys
import yaml
from sqlalchemy import create_engine, text
import datetime
import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import traceback

from global_config.config import yaml_config_boxed
from global_config.logger_config import logger

logger.name = os.path.basename(__file__)

# ========== 配置 ==========
DB_CONFIGS = {
    "Postgres": yaml_config_boxed.gui.postgres.db_conn2,
    "Ubuntu_Postgres": yaml_config_boxed.gui.ubuntu_postgres.db_conn2
}

def run_query(db_key, sql, params=None):
    try:
        cfg = DB_CONFIGS[db_key]
        conn = create_engine(cfg)
        with conn.connect() as connection:
            df = pd.read_sql(text(sql), connection, params=params)
            return df
    except Exception as e:
        logger.error(f"SQL执行错误: {sql}, 错误详情: {str(e)}\n{traceback.format_exc()}")
        return pd.DataFrame()

def run_scalar(db_key, sql):
    try:
        cfg = DB_CONFIGS[db_key]
        conn = create_engine(cfg)
        # 使用 SQLAlchemy 的 execute 方法来执行查询
        with conn.connect() as connection:
            result = connection.execute(text(sql))
            row = result.fetchone()
            val = None
            # 更安全的处理方法，避免list index out of range错误
            if row is not None and len(row) > 0:
                val = row[0]
            return val
    except Exception as e:
        logger.error(f"SQL执行错误: {sql}, 错误详情: {str(e)}\n{traceback.format_exc()}")
        return None

# ========== 核心查询SQL ==========
BASE_TRANSCRIPTION_LOG_SQL = """
SELECT 
    tl.id,
    tl.file_id,
    tl.path,
    tl.status,
    tl.started_at,
    tl.ended_at,
    tl.duration_secs,
    tl.error_message,
    tl.model_used,
    tl.embedding_model,
    tl.model_in_out,
    tl.version,
    tl.file_md5
FROM transcription_log tl
WHERE (tl.status IS NULL OR tl.status = '' OR tl.status = :status)
ORDER BY tl.ended_at DESC
"""

TRANSCRIPT_SEGMENTS_SQL = """
SELECT * FROM transcript_segment ts 
WHERE ts.file_id = :file_id
ORDER BY ts.created_at
"""

# ========== 创建 Dash 应用 ==========
app = dash.Dash(__name__, 
                external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'],
                suppress_callback_exceptions=True)

# ========== 布局 ==========
app.layout = html.Div([
    html.H1("转录数据查询器", style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # 数据源选择
    html.Div([
        html.H3("选择数据源", style={'marginBottom': '20px'}),
        dcc.Checklist(
            id='checkbox-postgres',
            options=[{'label': 'Postgres', 'value': 'postgres'}],
            value=[],  # Default to unchecked
            style={'display': 'inline-block', 'marginRight': '20px'}
        ),
        dcc.Checklist(
            id='checkbox-ubuntu-postgres',
            options=[{'label': 'Ubuntu_Postgres', 'value': 'ubuntu_postgres'}],
            value=[],  # Default to unchecked
            style={'display': 'inline-block', 'marginRight': '10px'}
        ),
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # 状态筛选
    html.Div([
        html.H3("状态筛选", style={'marginBottom': '20px'}),
        dcc.Dropdown(
            id='status-filter',
            options=[
                {'label': '全部', 'value': ''},
                {'label': '成功', 'value': 'success'},
                {'label': '错误', 'value': 'error'}
            ],
            value='',  # Default to show all
            style={'width': '150px', 'display': 'inline-block', 'marginRight': '10px'}
        ),
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # 分页控件
    html.Div([
        html.Label("每页数量:", style={'marginRight': '10px'}),
        dcc.Dropdown(
            id='dropdown-page-size',
            options=[{'label': str(i), 'value': i} for i in [10, 20, 50, 100]],
            value=20,
            style={'width': '150px', 'display': 'inline-block', 'marginRight': '10px'}
        ),
        html.Label("自定义:", style={'marginRight': '10px'}),
        dcc.Input(id='input-custom-page-size', type='number', value=20, min=1, style={'width': '80px', 'display': 'inline-block'}),
        html.Button("应用", id='button-apply-page-size', n_clicks=0, style={'marginLeft': '20px'}),
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # 分页状态
    html.Div(id='page-status', style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # 主要数据表格
    html.Div([
        html.H3("转录日志查询", style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(id='transcription-log-table', style={'marginBottom': '30px'}),
    ]),
    
    # 转录片段详情
    html.Div([
        html.H3("转录片段详情", style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(id='transcript-segments-display', style={'marginBottom': '30px'}),
    ]),
    
    # 隐藏的存储区域
    html.Div(id='hidden-store', style={'display': 'none'}),
])

# ========== 回调函数 ==========
@app.callback(
    Output('page-status', 'children'),
    Input('dropdown-page-size', 'value'),
    Input('input-custom-page-size', 'value'),
    Input('button-apply-page-size', 'n_clicks'),
    State('page-status', 'children')
)
def update_page_status(page_size, custom_size, n_clicks, current_status):
    # 用于存储当前分页配置
    if n_clicks > 0:
        # 检查输入是否为有效数字
        if custom_size and isinstance(custom_size, (int, float)) and custom_size > 0:
            page_size = int(custom_size)
        else:
            page_size = 20  # 默认值
    return f"当前分页配置: {page_size} 条/页"

@app.callback(
    Output('transcription-log-table', 'children'),
    Input('checkbox-postgres', 'value'),
    Input('checkbox-ubuntu-postgres', 'value'),
    Input('status-filter', 'value'),
    Input('dropdown-page-size', 'value'),
    Input('input-custom-page-size', 'value'),
    Input('button-apply-page-size', 'n_clicks'),
    State('hidden-store', 'children')
)
def update_transcription_log_table(postgres_selected, ubuntu_postgres_selected, status_filter, page_size, custom_size, n_clicks, stored_data):
    selected_dbs = []
    # Handle checkbox values for Checklist components properly
    if postgres_selected and 'postgres' in postgres_selected:
        selected_dbs.append("Postgres")
    if ubuntu_postgres_selected and 'ubuntu_postgres' in ubuntu_postgres_selected:
        selected_dbs.append("Ubuntu_Postgres")
    
    if not selected_dbs:
        return html.Div("请至少选择一个数据源进行查询。", style={'color': 'red', 'textAlign': 'center'})
    
    # 为每个数据源单独处理
    all_tables = []
    for db in selected_dbs:
        try:
            # 获取总记录数
            sql_count = "SELECT COUNT(*) FROM transcription_log tl"
            total_records = run_scalar(db, sql_count)
            if total_records is None:
                total_records = 0
            
            # 确定分页大小
            if n_clicks > 0 and custom_size and isinstance(custom_size, (int, float)) and custom_size > 0:
                page_size = int(custom_size)
            elif page_size is None:
                page_size = 20
                
            # 为每个数据源创建独立的分页组件
            offset = 0  # 简化版本
            sql_with_pagination = BASE_TRANSCRIPTION_LOG_SQL + f" LIMIT {page_size} OFFSET {offset}"
            
            # Add parameters for status filter
            params = {}
            if status_filter is not None:
                params['status'] = status_filter
            
            df = run_query(db, sql_with_pagination, params=params)
            
            if not df.empty:
                # 创建表格
                table = html.Table([
                    html.Thead(html.Tr([html.Th(col) for col in df.columns])),
                    html.Tbody([
                        html.Tr([
                            html.Td(str(row['id'])),
                            html.Td(str(row['file_id'])),
                            html.Td(str(row['path'])),
                            html.Td(str(row['status'])),
                            html.Td(str(row['started_at']) if pd.notna(row['started_at']) else ''),
                            html.Td(str(row['ended_at']) if pd.notna(row['ended_at']) else ''),
                            html.Td(str(row['duration_secs']) if pd.notna(row['duration_secs']) else ''),
                            html.Td(str(row['error_message']) if pd.notna(row['error_message']) else ''),
                            html.Td(str(row['model_used'])),
                            html.Td(str(row['model_in_out'])),
                            html.Td(str(row['version'])),
                            html.Td(str(row['file_md5'])),
                            html.Td(html.Button("查看详情", 
                                              id={'type': 'view-button', 'index': row['file_id']}, 
                                              n_clicks=0,
                                              style={'padding': '5px 10px', 'fontSize': '12px'}))
                        ]) for _, row in df.iterrows()
                    ])
                ], style={'width': '100%', 'border': '1px solid #ccc', 'marginBottom': '20px'})
                
                all_tables.append(html.Div([
                    html.H4(f"数据源：{db}"),
                    table
                ], style={'marginBottom': '40px'}))
                
            else:
                all_tables.append(html.Div(f"没有找到转录日志记录 (数据源: {db})", style={'color': 'gray', 'textAlign': 'center'}))
                
        except Exception as e:
            return html.Div(f"处理数据源 {db} 时出错: {str(e)}", style={'color': 'red', 'textAlign': 'center'})
    
    return all_tables

@app.callback(
    Output('transcript-segments-display', 'children'),
    Input({'type': 'view-button', 'index': dash.ALL}, 'n_clicks'),
    State('hidden-store', 'children')
)
def display_transcript_segments(n_clicks_list, stored_data):
    # 从点击事件中获取文件ID
    ctx = dash.callback_context
    logger.info(f"Triggered button by ctx.triggered: {ctx.triggered}")
    if not ctx.triggered:
        return html.Div("点击转录日志中的'查看详情'按钮以查看片段。", style={'color': 'gray', 'textAlign': 'center'})
    
    # Properly extract file_id from button ID
    button_prop_id = ctx.triggered[0]['prop_id']
    logger.info(f"Triggered button prop_id: {button_prop_id}")
    # Get the index part from button ID like '{"index":271828,"type":"view-button"}.n_clicks'
    if '.' in button_prop_id:
        button_id = button_prop_id.split('.')[0]  # Extract '{"index":271828,"type":"view-button"}'
        # Parse the index properly for dash callbacks
        import json
        try:
            id_json = json.loads(button_id)  # Ensure it's valid JSON
            logger.info(f"Triggered button id_json: {id_json}")
            # For '{"index":271828,"type":"view-button"}', extract 271828 as file_id
            file_id = int(id_json['index'])
        except (ValueError, IndexError):
            traceback.print_exc()
            file_id = None
    else:
        file_id = None
    
    # 查询转录片段
    if file_id is None:
        return html.Div("无法获取文件ID", style={'color': 'red', 'textAlign': 'center'})
    logger.info(f"Triggered button get file_id: {file_id}")
    
    # 查询转录片段
    try:
        segments_df = run_query("Postgres", TRANSCRIPT_SEGMENTS_SQL, params={"file_id":file_id})
        
        if not segments_df.empty:
            # 创建时间轴可视化
            fig = px.line(segments_df, x='created_at', y='start_time', 
                         title=f"转录片段时间轴 (文件ID: {file_id})",
                         labels={'created_at': '创建时间', 'start_time': '开始时间'},
                         markers=True)
            
            fig.update_layout(
                height=400,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis_title="时间",
                yaxis_title="时间 (秒)"
            )
            
            return html.Div([
                html.H4(f"转录片段详情 (文件ID: {file_id})"),
                dcc.Graph(figure=fig),
                html.H5("转录片段数据表:"),
                html.Table([
                    html.Thead(html.Tr([html.Th(col) for col in segments_df.columns])),
                    html.Tbody([
                        html.Tr([
                            html.Td(str(cell)) for cell in row
                        ]) for _, row in segments_df.iterrows()
                    ])
                ], style={'width': '100%', 'border': '1px solid #ccc', 'marginTop': '20px'})
            ])
        else:
            return html.Div("没有找到该文件的转录片段", style={'color': 'gray', 'textAlign': 'center'})
            
    except Exception as e:
        return html.Div(f"查询文件 {file_id} 的转录片段时出错: {str(e)}", style={'color': 'red', 'textAlign': 'center'})

# ========== 运行应用 ==========
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
