import os
import streamlit as st

from v03_srt_merger_llm_func import *

st.set_page_config(layout="wide")


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
