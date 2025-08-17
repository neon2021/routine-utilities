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