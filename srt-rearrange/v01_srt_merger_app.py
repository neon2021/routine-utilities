import os
import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import timedelta

# 模型初始化
@st.cache_resource
def load_model():
    # return SentenceTransformer('all-MiniLM-L6-v2')
    # return SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    # return SentenceTransformer('intfloat/multilingual-e5-large')
    return SentenceTransformer('intfloat/e5-large-v2')
    # return SentenceTransformer('BAAI/bge-m3')



model = load_model()

def time_to_timedelta(t):
    h, m, s_ms = t.split(":")
    s, ms = s_ms.split(",")
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

def parse_srt(srt_content):
    pattern = re.compile(r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)\s+(?=\d+\s+\d{2}|\Z)", re.DOTALL)
    entries = []
    for match in pattern.finditer(srt_content):
        index = int(match.group(1))
        start = match.group(2)
        end = match.group(3)
        text = match.group(4).replace("\n", " ").strip()
        entries.append({"index": index, "start": start, "end": end, "text": text})
    return entries

def semantic_similarity(sent1, sent2, threshold=0.75):
    emb1 = model.encode([sent1])[0]
    emb2 = model.encode([sent2])[0]
    sim = cosine_similarity([emb1], [emb2])[0][0]
    print(f'\n\nsent1: "{sent1}"\nsent2: "{sent2}"\nsim: {sim}')
    return sim > threshold

def merge_entries(entries, time_gap_threshold=1.5, sim_threshold=0.75):
    merged = []
    buffer = [entries[0]]
    for curr in entries[1:]:
        prev = buffer[-1]
        prev_end = time_to_timedelta(prev["end"])
        curr_start = time_to_timedelta(curr["start"])
        gap = (curr_start - prev_end).total_seconds()
        similarity = semantic_similarity(prev["text"], curr["text"], sim_threshold)
        if gap < time_gap_threshold and similarity:
            buffer.append(curr)
        else:
            merged.append({
                "start": buffer[0]["start"],
                "end": buffer[-1]["end"],
                "text": " ".join([b["text"] for b in buffer])
            })
            buffer = [curr]
    if buffer:
        merged.append({
            "start": buffer[0]["start"],
            "end": buffer[-1]["end"],
            "text": " ".join([b["text"] for b in buffer])
        })
    for i, entry in enumerate(merged, 1):
        entry["index"] = i
    return merged

# ⬇️ 缓存合并处理逻辑，只要 slider 参数或内容改变就重新执行
@st.cache_data(show_spinner="正在合并字幕中...")
def get_merged_results(srt_text: str, sim_threshold: float, gap_threshold: float):
    entries = parse_srt(srt_text)
    merged = merge_entries(entries, time_gap_threshold=gap_threshold, sim_threshold=sim_threshold)
    # print('merged results: \n')
    # for i in merged:
    #     print(i)
    return entries, merged

st.title("🎬 SRT 句子智能合并工具")

# ⬇️ 本地 SRT 读取（调试用），你也可以用上传方式
srt_file_path = os.path.join(os.path.dirname(__file__), 'example.srt')
with open(srt_file_path, 'r') as f:
    srt_text = f.read()

# ⬇️ 控制滑动条（触发重新计算）
sim_threshold = st.slider("语义相似度阈值", 0.5, 0.95, 0.75, 0.01)
gap_threshold = st.slider("最大时间间隔（秒）", 0.1, 5.0, 1.5, 0.1)

# ⬇️ 自动重新处理
entries, merged = get_merged_results(srt_text, sim_threshold, gap_threshold)

# 展示
st.subheader("原始字幕片段")
for e in entries[:10]:
    st.text(f"[{e['start']} → {e['end']}] {e['text']}")

st.subheader("🔁 合并结果")
for e in merged[:10]:
    st.markdown(f"**[{e['start']} → {e['end']}]** {e['text']}")

# 下载
st.download_button("📥 下载合并后字幕", 
                   data="\n\n".join([f"{e['index']}\n{e['start']} --> {e['end']}\n{e['text']}" for e in merged]),
                   file_name="merged_output.srt",
                   mime="text/plain")
