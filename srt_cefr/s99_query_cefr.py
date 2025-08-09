import sqlite3
import json
import sys
from global_config.config import other_dir

from global_config.logger_config import logger

def query(input_string:str):
    word_list = [w.strip().lower() for w in input_string.split(",") if w.strip()]

    # 连接 SQLite
    db_path = "/tmp/evp_words.db"
    logger.info(f'db_path: {db_path}')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查询定义
    result = []
    for word in word_list:
        cursor.execute("""
        SELECT base_word, guideword, level, part_of_speech, topic, details 
        FROM evp_words 
        WHERE LOWER(base_word) = ?
        """, (word,))
        rows = cursor.fetchall()
        for row in rows:
            result.append({
                "Base Word": row[0],
                "Guideword": row[1],
                "Level": row[2],
                "Part of Speech": row[3],
                "Topic": row[4],
                "Details": row[5]
            })

    conn.close()

    # 输出 JSON 字符串
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) < 2:
        logger.info("Usage: python query_words.py \"word1, word2, ...\"")
        
        demo_str = "hello, world, test, program, query"
        logger.info(f"For example: python query_words.py \"{demo_str}\"")
        query(demo_str)
        sys.exit(1)

    # 解析输入单词
    input_string = sys.argv[1]
    query(input_string)