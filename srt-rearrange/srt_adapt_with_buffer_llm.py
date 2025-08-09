from collections import deque
import requests
from global_config.config import yaml_config_boxed

remote_host = yaml_config_boxed.ollama.remote_host

# ========== Ollama 接口 ==========
def ask_ollama(prompt, model="gemma3:4b-it-q8_0"):
    """向 Ollama 模型发送 prompt 并返回文本结果"""
    response = requests.post(f"http://{remote_host}:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        # messages=[
        #     {"role": "system", "content": "You are a text segmentation assistant."},
        #     {"role": "user", "content": prompt}
        # ]
    )
    print(f'model: {model}; prompt:{prompt}, response: {response.json()}')
    
    return response.json()['response'].strip()

def check_complete_sentence(text):
    """使用 Ollama 判断文本是否为完整句子"""
    prompt = f"""
Determine if the following text is a complete English sentence:
---
{text}
---
Answer only YES or NO.
"""
    result = ask_ollama(prompt)
    return "YES" in result.upper()


# ========== 句子处理逻辑 ==========
def process_full_sentence(buffer, results):
    """
    情况2：从buffer开头开始识别完整句子
    - 输出完整句子
    - 移除已组成完整句子的部分
    """
    for i in range(len(buffer)):
        candidate = " ".join(list(buffer)[:i + 1])
        if check_complete_sentence(candidate):
            # 输出完整句子
            full_sentence = " ".join(list(buffer)[:i + 1])
            results.append(full_sentence)
            print(f"✅ 识别完整句子: {full_sentence}")
            # 移除已输出部分
            for _ in range(i + 1):
                buffer.popleft()
            return True
    return False


def process_full_buffer(buffer, results):
    """
    情况1增强版：buffer已满但未识别完整句子
    - 优先尝试从2-5句中拼完整句子
    - 根据是否使用了第5句内容决定是否清空buffer
    """
    print("⚠️ Buffer已满，尝试2-5句识别完整句子...")

    # 尝试从第2句开始拼接
    for i in range(1, len(buffer)):
        candidate = " ".join(list(buffer)[1:i + 1])
        if check_complete_sentence(candidate):
            # 输出第一句
            first_sentence = buffer[0]
            results.append(first_sentence)
            print(f"➡️ 输出第一句: {first_sentence}")

            # 输出2-5句完整句子
            full_sentence = " ".join(list(buffer)[1:i + 1])
            results.append(full_sentence)
            print(f"✅ 输出2-5句完整句子: {full_sentence}")

            # 清理 buffer
            if i == len(buffer) - 1:
                buffer.clear()
                print("🧹 完整句子用完了第5句，buffer清空")
            else:
                # 保留第5句剩余部分
                last_part = buffer[-1]
                buffer.clear()
                buffer.append(last_part)
                print("🧹 只清理1-4句，保留第5句")
            return True

    # 如果2-5句也无法组成完整句子 → 输出第1句
    first_sentence = buffer.popleft()
    results.append(first_sentence)
    print(f"⚠️ 无完整句子，输出第一个: {first_sentence}")
    return False


def segment_sentences(segments, max_buffer=5):
    buffer = deque(maxlen=max_buffer)
    results = []

    for seg in segments:
        buffer.append(seg.strip())
        print(f"\n加入片段: {seg}")

        # 情况2：从buffer开头识别完整句子
        if process_full_sentence(buffer, results):
            continue

        # 情况1：buffer已满时触发增强逻辑
        if len(buffer) == max_buffer:
            process_full_buffer(buffer, results)

    # 处理剩余buffer（尾部可能不完整）
    while buffer:
        results.append(buffer.popleft())

    return results


# ========== 测试 ==========
if __name__ == "__main__":
    segments = [
        "near done. I'm on my way",
        "to home by train as fast as",
        "possible. Today is great to",
        "meet my old friends. That sounds",
        "wonderful and I can't wait",
        "to see them later tonight."
    ]

    sentences = segment_sentences(segments)
    print("\n最终输出结果:")
    for s in sentences:
        print("-", s)
