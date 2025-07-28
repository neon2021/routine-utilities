import os
import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import timedelta
import re

st.set_page_config(layout="wide")

# 支持的模型列表
MODELS = {
    "MiniLM": "all-MiniLM-L6-v2",
    # "MPNet-Multilingual": "paraphrase-multilingual-mpnet-base-v2",
    # "E5-Large-v2": "intfloat/e5-large-v2",
}

# 缓存加载多个模型
@st.cache_resource
def load_models():
    return {name: SentenceTransformer(path) for name, path in MODELS.items()}

models = load_models()

# 字幕时间格式处理
def time_to_timedelta(t):
    h, m, s_ms = t.split(":")
    s, ms = s_ms.split(",")
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

# 解析 SRT 文件
def parse_srt(srt_content):
    pattern = re.compile(r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)\s+(?=\d+\s+\d{2}|\Z)", re.DOTALL)
    entries = []
    for match in pattern.finditer(srt_content):
        entries.append({
            "index": int(match.group(1)),
            "start": match.group(2),
            "end": match.group(3),
            "text": match.group(4).replace("\n", " ").strip()
        })
    return entries


import spacy

@st.cache_resource
def load_spacy():
    return spacy.load("en_core_web_sm")

nlp = load_spacy()

import re

# def should_merge(prev_text, curr_text, similarity, sim_threshold, gap_sec):
#     # rule 1: semantic similarity
#     if gap_sec < 1.5 and similarity > sim_threshold:
#         return True

#     prev_text = prev_text.strip()
#     curr_text = curr_text.strip()
#     if not prev_text or not curr_text:
#         return False

#     # rule 2: simple structure clues
#     prev_ends_punct = prev_text[-1] in ".!?,，。！？"
#     curr_first_word = curr_text.split()[0].lower()

#     conj_starters = {'and', 'but', 'plus', 'also', 'then', 'so', 'or'}
#     verb_starters = {'to', 'deport', 'resume', 'support', 'give', 'take', 'stop'}

#     if not prev_ends_punct and (curr_first_word in conj_starters or curr_first_word in verb_starters):
#         return True

#     # rule 3: to + verb structure
#     if prev_text.endswith('to') and curr_first_word in verb_starters:
#         return True

#     # ✅ rule 4: SpaCy-based structure analysis
#     prev_doc = nlp(prev_text)
#     curr_doc = nlp(curr_text)

#     # 前一句没有主语或动词结尾，可能是残句
#     prev_incomplete = all(tok.dep_ not in {'ROOT'} for tok in prev_doc)

#     # 当前句以动词或连词开头，可能是补语
#     curr_starts_with_verb_or_conj = (
#         curr_doc[0].pos_ in {'VERB', 'AUX', 'CCONJ', 'PART', 'ADP'}  # 动词、助动词、连词、介词
#     )

#     if prev_incomplete and curr_starts_with_verb_or_conj:
#         return True

#     return False

# def should_merge(prev_text, curr_text, similarity, sim_threshold, gap_sec):
#     nlp = load_spacy()  # cached load

#     if gap_sec < 1.5 and similarity > sim_threshold:
#         return True

#     prev_text = prev_text.strip()
#     curr_text = curr_text.strip()
#     if not prev_text or not curr_text:
#         return False

#     prev_doc = nlp(prev_text)
#     curr_doc = nlp(curr_text)

#     prev_ends_punct = prev_text[-1] in ".!?。！？"
#     curr_first_token = curr_doc[0] if curr_doc else None
#     prev_last_token = prev_doc[-1] if prev_doc else None

#     # rule: 补句连词、动词开头（简单）
#     if not prev_ends_punct and curr_first_token and curr_first_token.text.lower() in {
#         'and', 'but', 'plus', 'also', 'then', 'so', 'to', 'deport'
#     }:
#         return True

#     # rule: to + verb
#     if prev_text.endswith('to') and curr_first_token and curr_first_token.pos_ == "VERB":
#         return True

#     # ✅ rule: 前句以介词结尾，后句以名词开头
#     if prev_last_token and curr_first_token:
#         if prev_last_token.pos_ == "ADP" and curr_first_token.pos_ in {"NOUN", "PROPN", "DET"}:
#             return True

#     # ✅ rule: 前句以关系词（which, where, that）结尾，后句是从句补充
#     if prev_last_token and prev_last_token.text.lower() in {"where", "which", "that"}:
#         return True

#     return False

def should_merge_old(prev_text, curr_text, similarity, sim_threshold, gap_sec):
    nlp = load_spacy()  # 使用 Streamlit cache_resource

    # Rule 1: 语义相似度 + 时间间隔
    if gap_sec < 1.5 and similarity > sim_threshold:
        return True

    prev_text = prev_text.strip()
    curr_text = curr_text.strip()
    if not prev_text or not curr_text:
        return False

    prev_doc = nlp(prev_text)
    curr_doc = nlp(curr_text)

    # 获取有效 token（去除空格和标点）
    prev_tokens = [t for t in prev_doc if not t.is_space]
    curr_tokens = [t for t in curr_doc if not t.is_space]

    if not prev_tokens or not curr_tokens:
        return False

    prev_last = prev_tokens[-1]
    curr_first = curr_tokens[0]

    # Rule 2: 常见补句连接词（and, but, to 等）
    if prev_text[-1] not in ".!?，。！？" and curr_first.text.lower() in {
        'and', 'but', 'plus', 'also', 'then', 'so', 'to', 'deport', 'from'
    }:
        return True

    # Rule 3: 前句以 "to" 结尾 + 后句动词
    if prev_last.text.lower() == 'to' and curr_first.pos_ in {"VERB", "AUX"}:
        return True

    # ✅ Rule 4: 前句以介词结尾 + 后句以名词/专有名词/限定词开头
    if prev_last.pos_ == "ADP" and curr_first.pos_ in {"NOUN", "PROPN", "DET"}:
        return True

    # ✅ Rule 5: 前句以关系词结尾（which, where, that）+ 后句从句结构
    if prev_last.text.lower() in {"where", "which", "that"}:
        return True

    # ✅ Rule 6: 前句以 "back where" 或 "from the" 等常见结构结尾
    prev_phrase = prev_text.strip().lower()
    if prev_phrase.endswith("from the") or prev_phrase.endswith("back where"):
        return True
    
    # ✅ Rule 7: 前句以 how/when/why 等引导词结尾，后句以副词/介词短语开头
    if prev_last.text.lower() in {"how", "when", "why"} and curr_first.pos_ in {"ADP", "ADV"}:
        return True

    return False

import requests

def query_ollama_merge_decision(prev, curr, model="gemma:7b"):
    prompt = f"""请判断下面两个字幕是否属于同一个完整句子（即它们构成一个完整的语法单元，不应断开）。

字幕1：
{prev}

字幕2：
{curr}

是否应合并？只回答“是”或“否”。"""
    
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
    })
    print(f'model: {model}; prompt:{prompt}')
    reply = response.json()["response"].strip()
    print(f'reply:{reply}')
    return reply.startswith("是")


def should_merge(prev_text, curr_text, similarity, sim_threshold, gap_sec):
    # 优先调用 Ollama + gemma 进行判断
    try:
        if query_ollama_merge_decision(prev_text, curr_text, model="gemma3:4b"):
            # print(f"✅ 合并（gemma判断）: \n  prev: {prev_text}\n  curr: {curr_text}")
            return True
    except Exception as e:
        print(f"⚠️ Ollama 请求失败，降级使用相似度判断：{e}")

    # fallback
    return should_merge_old(prev_text, curr_text, similarity, sim_threshold, gap_sec)


# 合并逻辑（传入模型）
def merge_entries(entries, model, time_gap_threshold=1.5, sim_threshold=0.75):
    merged = []
    buffer = [entries[0]]
    for curr in entries[1:]:
        prev = buffer[-1]
        prev_end = time_to_timedelta(prev["end"])
        curr_start = time_to_timedelta(curr["start"])
        gap = (curr_start - prev_end).total_seconds()

        emb1 = model.encode([prev["text"]])[0]
        emb2 = model.encode([curr["text"]])[0]
        similarity = cosine_similarity([emb1], [emb2])[0][0]

        if should_merge(prev["text"], curr["text"], similarity, sim_threshold, gap):
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
    for i, m in enumerate(merged, 1):
        m["index"] = i
    return merged

# 合并并缓存每个模型结果
@st.cache_data(show_spinner="🧠 模型合并处理中...")
def get_all_model_outputs(srt_text, sim_threshold, gap_threshold):
    entries = parse_srt(srt_text)
    results = {}
    for name, model in models.items():
        merged = merge_entries(entries, model, gap_threshold, sim_threshold)
        results[name] = merged
    return entries, results

# SRT 文件读取
srt_path = os.path.join(os.path.dirname(__file__), "example.srt")
with open(srt_path, 'r') as f:
    srt_text = f.read()

# 控件区
st.sidebar.title("🔧 设置参数")
sim_threshold = st.sidebar.slider("语义相似度阈值", 0.5, 0.95, 0.75, 0.01)
gap_threshold = st.sidebar.slider("最大时间间隔（秒）", 0.1, 5.0, 1.5, 0.1)

entries, all_results = get_all_model_outputs(srt_text, sim_threshold, gap_threshold)

# 并排显示原文 + 多模型结果
cols = st.columns(len(models) + 1)

with cols[0]:
    st.markdown("### 📜 原始字幕")
    for e in entries[:20]:
        st.text(f"[{e['start']} → {e['end']}] {e['text']}")

for i, (name, merged) in enumerate(all_results.items(), start=1):
    with cols[i]:
        st.markdown(f"### 🤖 {name}")
        for e in merged[:10]:
            st.markdown(f"**[{e['start']} → {e['end']}]** {e['text']}")
