import os
import pandas as pd
import calendar
from datetime import datetime
import xlsxwriter

excel_file_path = os.path.expanduser("~/Documents/data_db-in-documents/training_calendar_2025_full.xlsx")

# 读取训练数据
df = pd.read_csv(os.path.expanduser("~/Documents/data_db-in-documents/gym_exercise_sessions_202507110825.csv"))
df["fmt_exercise_date"] = pd.to_datetime(df["fmt_exercise_date"])

# 映射动作→身体部位（可自行补全）
movement_to_bodypart = {
    "CRUNCH": "ABS",
    "CURL": "ARM",
    "LEG_PRESS": "LEG",
    "FARMERS_WALK": "GRIP",
    "CHEST_PRESS_WITH_BAND": "CHEST",
    "DUMBBELL_BICEPS_CURL": "ARM",
    "BENCH_PRESS": "CHEST",
    "SHOULDER_PRESS": "SHOULDER",
    "DIAMOND_PUSH_UP": "TRICEPS",
    "BENCH_DIP": "TRICEPS",
}

# 聚合每天每个动作的训练总量
agg_info = (
    df.groupby(["fmt_exercise_date", "fmt_movement"])
    .agg({"weight": "sum", "repetition_count": "sum"})
    .reset_index()
)

movement_dates = df.groupby("fmt_movement")["fmt_exercise_date"].apply(lambda x: sorted(set(x))).to_dict()
latest_date = df["fmt_exercise_date"].max()

# 日期 → 动作字典
date_to_movements = agg_info.groupby("fmt_exercise_date").apply(
    lambda g: {
        row["fmt_movement"]: {"weight": row["weight"], "reps": row["repetition_count"]}
        for _, row in g.iterrows()
    }
).to_dict()

# 定义颜色样式函数
def get_color_fmt(workbook, move, date):
    dates = movement_dates.get(move, [])
    if date not in dates:
        return None
    idx = dates.index(date)
    if idx > 0:
        delta = (date - dates[idx - 1]).days
        color = "#C6EFCE" if delta == 1 else "#BDD7EE"  # green or blue
    else:
        color = None
    if (latest_date - date).days > 3 and date == dates[-1]:
        color = "#F4CCCC"  # red
    fmt = workbook.add_format({"text_wrap": True, "valign": "top"})
    if color:
        fmt.set_bg_color(color)
    return fmt

# 生成 Excel 文件
output = excel_file_path
workbook = xlsxwriter.Workbook(output)
bold = workbook.add_format({"bold": True, "align": "center"})
wrap = workbook.add_format({"text_wrap": True, "valign": "top"})

months = [(2025, m) for m in range(1, 8)]

# Sheet 1: 横向日历
sheet1 = workbook.add_worksheet("按月横向排列")
col_base = 0
for y, m in months:
    cal = calendar.Calendar(firstweekday=6).monthdayscalendar(y, m)
    sheet1.write(0, col_base, f"{calendar.month_name[m]} {y}", bold)
    for i, wd in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
        sheet1.write(1, col_base + i, wd, bold)
    for w_idx, week in enumerate(cal):
        for d_idx, day in enumerate(week):
            if day == 0:
                continue
            cur_date = datetime(y, m, day)
            sheet1.write(2 + w_idx * 4, col_base + d_idx, str(day), bold)
            movements = date_to_movements.get(cur_date, {})
            for r, (move, stat) in enumerate(movements.items()):
                txt = f"{move}\n{int(stat['weight'])}kg x {int(stat['reps'])}"
                fmt = get_color_fmt(workbook, move, cur_date) or wrap
                sheet1.write(3 + w_idx * 4 + r, col_base + d_idx, txt, fmt)
    for i in range(7):
        sheet1.set_column(col_base + i, col_base + i, 20)
    col_base += 8

# Sheet 2: 纵向日历
sheet2 = workbook.add_worksheet("按月纵向排列")
row_base = 0
for y, m in months:
    cal = calendar.Calendar(firstweekday=6).monthdayscalendar(y, m)
    sheet2.write(row_base, 0, f"{calendar.month_name[m]} {y}", bold)
    for i, wd in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
        sheet2.write(row_base + 1, i, wd, bold)
    for w_idx, week in enumerate(cal):
        for d_idx, day in enumerate(week):
            if day == 0:
                continue
            cur_date = datetime(y, m, day)
            sheet2.write(row_base + 2 + w_idx * 4, d_idx, str(day), bold)
            movements = date_to_movements.get(cur_date, {})
            for r, (move, stat) in enumerate(movements.items()):
                txt = f"{move}\n{int(stat['weight'])}kg x {int(stat['reps'])}"
                fmt = get_color_fmt(workbook, move, cur_date) or wrap
                sheet2.write(row_base + 3 + w_idx * 4 + r, d_idx, txt, fmt)
    row_base += len(cal) * 4 + 5

# Sheet 3: 每月训练量按身体部位汇总
sheet3 = workbook.add_worksheet("每月训练总览")
summary = []
for y, m in months:
    start = datetime(y, m, 1)
    end = datetime(y, m, calendar.monthrange(y, m)[1])
    sub = df[(df["fmt_exercise_date"] >= start) & (df["fmt_exercise_date"] <= end)].copy()
    sub["bodypart"] = sub["fmt_movement"].map(movement_to_bodypart).fillna("OTHER")
    grp = sub.groupby("bodypart").agg(
        total_weight_kg=("weight", "sum"),
        total_reps=("repetition_count", "sum")
    ).reset_index()
    grp["month"] = f"{y}-{m:02d}"
    summary.append(grp)

monthly_summary = pd.concat(summary)
cols = ["month", "bodypart", "total_weight_kg", "total_reps"]
for i, col in enumerate(cols):
    sheet3.write(0, i, col, bold)
for r, row in enumerate(monthly_summary[cols].itertuples(index=False), start=1):
    for c, val in enumerate(row):
        sheet3.write(r, c, val)

workbook.close()
print(f"✅ 文件已生成：{output}")
