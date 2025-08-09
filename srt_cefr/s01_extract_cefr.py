from bs4 import BeautifulSoup
from lxml import etree
import os

from global_config.config import other_dir

# === Step 1: 加载并清除 <style> ===
with open(other_dir(__file__, "resources/EVP-CEFR-british-vocabulary-list.html"), "r", encoding="utf-8") as f:
    html_content = f.read()
# === Step 2: 写入中间临时文件（格式化输出） ===

soup = BeautifulSoup(html_content, "lxml")

# 删除所有 <style> 标签
for style_tag in soup.find_all("style"):
    style_tag.decompose()

# 删除所有标签的 style 属性
for tag in soup.find_all(attrs={"style": True}):
    del tag["style"]
    
# === Step 2: 写入中间临时文件 ===
with open("/tmp/out.html", mode="w", encoding="utf-8") as tmpfile:
    tmpfile.write(soup.prettify())  # 使用 prettify 格式化 HTML
    temp_html_path = tmpfile.name

print(f'temp_html_path: {temp_html_path}')