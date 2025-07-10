import os
import pandas as pd
from datetime import timedelta
from dash import Dash, html, dcc
import plotly.graph_objs as go

# 读取 CSV 数据
df = pd.read_csv(os.path.expanduser("~/Documents/data_db-in-documents/gym_exercise_sessions_202507090754.csv"))
df["fmt_exercise_date"] = pd.to_datetime(df["fmt_exercise_date"])

# 今日与昨日
today = df["fmt_exercise_date"].max()
yesterday = today - timedelta(days=1)

# 昨日练过的动作
yesterday_movements = set(df[df["fmt_exercise_date"] == yesterday]["fmt_movement"])

# 动作最后一次出现时间 (30 天内)
recent_df = df[df["fmt_exercise_date"] >= today - timedelta(days=30)]
last_seen = recent_df.groupby("fmt_movement")["fmt_exercise_date"].max()

# 推荐动作 (昨天未练过, 距离今天越久越靠前)
candidates = last_seen[~last_seen.index.isin(yesterday_movements)]
candidates_days = (today - candidates).dt.days.sort_values(ascending=False)
recommend_list = candidates_days.index.tolist()

# 做成 dataframe
recommend_df = pd.DataFrame({
    "movement": recommend_list,
    "days_since_last": candidates_days.loc[recommend_list].values
})

# 造线条: 每个 movement 相邻日期的间隔
movement_dates = df.groupby("fmt_movement")["fmt_exercise_date"].apply(lambda x: sorted(set(x))).reset_index()
lines = []
for _, row in movement_dates.iterrows():
    name, dates = row["fmt_movement"], row["fmt_exercise_date"]
    for i in range(1, len(dates)):
        d1, d2 = dates[i - 1], dates[i]
        delta = (d2 - d1).days
        color = "green" if delta == 1 else "red"
        lines.append({"movement": name, "start": d1, "end": d2, "delta": delta, "color": color})

# 编程 Dash 界面
app = Dash(__name__)

# layout 包括推荐列表 + 日历显示
data_traces = []
for _, row in df.iterrows():
    data_traces.append(go.Scatter(
        x=[row["fmt_exercise_date"]],
        y=[row["fmt_movement"]],
        mode="markers",
        marker=dict(size=8, color="blue"),
        name=row["fmt_movement"]
    ))

# 添加连线
for line in lines:
    data_traces.append(go.Scatter(
        x=[line["start"], line["end"]],
        y=[line["movement"]] * 2,
        mode="lines",
        line=dict(color=line["color"], width=2),
        showlegend=False
    ))

# 显示 Dash App
app.layout = html.Div([
    html.H2("每日训练动作日历 + 次日推荐"),
    dcc.Graph(
        figure=go.Figure(
            data=data_traces,
            layout=go.Layout(
                title="动作时间线", 
                xaxis=dict(title="日期"), 
                yaxis=dict(title="动作", type="category")
            )
        ),
        style={"height": "600px"}
    ),
    html.H4("次日推荐动作 (按最久未练排序)"),
    html.Ul([html.Li(f"{row['movement']} 【{row['days_since_last']} 天未练】") for _, row in recommend_df.iterrows()])
])

if __name__ == '__main__':
    app.run_server(debug=True)
