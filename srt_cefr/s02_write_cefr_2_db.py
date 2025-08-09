from bs4 import BeautifulSoup
from lxml import html
import os
import re
import json
import sqlite3

from global_config.config import cur_dir

temp_html_path = "/tmp/out.html"

# === Step 3: 用 lxml + XPath 解析新 HTML 文件 ===
with open(temp_html_path, "r", encoding="utf-8") as f:
    cleaned_html = f.read()

tree = html.fromstring(cleaned_html)

# 找出 .baTaJaMj .Text
cols_xpath = f"//div[contains(@class,'baTaJaMj')]//div[contains(@class,'Text')]"
columns = [col_div.text_content().strip() for col_div in tree.xpath(cols_xpath)]
print(f'columns: {columns}')


# 找出 .baTaJaLu 
# .entry-xx .Text
word_outer_xpath = f"//div[contains(@class,'baTaJaLu')]"
word_tree = tree.xpath(word_outer_xpath)[0]
word_elements = [word_div for word_div in word_tree.xpath(".//div[contains(@class,'group-item')]")]

word_list = []
for word_elem in word_elements:
    filtered = [el.text_content().strip() for el in word_elem.xpath(".//div[contains(@class,'Text')]//div") if el.text_content()]
    word_list.append(filtered)

# word_list 是一个二维列表，每一项是一个词条的 6 列数据（可能缺少部分）
from itertools import zip_longest
word_dicts = [dict(zip_longest(columns, row, fillvalue='')) for row in word_list]

# 示例打印前3个
for item in word_dicts[:10]:
    print(item)

first_10 = word_dicts[0:10]
print(json.dumps(first_10, ensure_ascii=False, indent=2))


# SQLite 文件路径（可替换为实际路径）
db_path = "/tmp/evp_words.db"

# 建表 + 插入数据
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 创建表
cur.execute("""
CREATE TABLE IF NOT EXISTS evp_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_word TEXT,
    guideword TEXT,
    level TEXT,
    part_of_speech TEXT,
    topic TEXT,
    details TEXT,
    unique(base_word,guideword,level,part_of_speech)
)
""")

# 插入数据
for item in word_dicts:
    cur.execute("""
        INSERT or ignore INTO evp_words (base_word, guideword, level, part_of_speech, topic, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        item.get("Base Word", ""),
        item.get("Guideword", ""),
        item.get("Level", ""),
        item.get("Part of Speech", ""),
        item.get("Topic", ""),
        item.get("Details", "")
    ))

# 提交并关闭连接
conn.commit()
conn.close()