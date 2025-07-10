import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime
import os

# 读取数据
df = pd.read_csv(os.path.expanduser("~/Documents/data_db-in-documents/gym_exercise_sessions_202507090754.csv"))

# 确保日期格式正确
df["fmt_exercise_date"] = pd.to_datetime(df["fmt_exercise_date"])

# 生成每天去重后的 fmt_movement 标签
df_daily = (
    df.groupby("fmt_exercise_date")["fmt_movement"]
    # .apply(lambda x: "\n".join(sorted(set(x))))  # 去重 + 排序 + 合并
    # .apply(lambda x: "<br>".join(sorted(set(x))))  # 去重 + 排序 + 合并
    .apply(lambda x: sorted(set(x)))  # 去重
    .explode()
    .reset_index()
    .rename(columns={"fmt_exercise_date": "date", "fmt_movement": "title"})
)

# 转换为 calendar 所需格式
events = [
    {
        "title": row["title"],
        "start": row["date"].strftime("%Y-%m-%d"),
        "end": row["date"].strftime("%Y-%m-%d"),
        "allDay": True,
    }
    for _, row in df_daily.iterrows()
]

# Streamlit 页面布局
st.title("🏋️‍♀️ 每日训练动作日历（多月展示）")
st.write("下方日历展示了每一天你训练过的动作组合")

calendar_options = {
    "initialView": "multiMonthYear",
    "editable": False,
    "height": 700,
    "firstDay": 1,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,multiMonthYear"
    },
    "views": {
        "multiMonthYear": {
            "type": "multiMonth",
            "duration": {"months": 3},
            "label": "3个月视图"
        }
    }
}

calendar(events=events, options=calendar_options)
