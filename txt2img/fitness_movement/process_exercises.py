import os
import json
import re
import requests
from typing import List, Dict, Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fpdf import FPDF
from ebooklib import epub
from bs4 import BeautifulSoup

def get_cefr_level(word: str) -> str:
    """获取单词的CEFR等级"""
    # 这里使用一个简单的映射，实际应用中应该使用更准确的CEFR等级数据
    cefr_map = {
        'a': 'A1', 'and': 'A1', 'at': 'A1', 'back': 'A1', 'ball': 'A1', 'bar': 'A1',
        'base': 'A1', 'body': 'A1', 'box': 'A1', 'chest': 'A1', 'core': 'A1',
        'down': 'A1', 'front': 'A1', 'grip': 'A1', 'hold': 'A1', 'in': 'A1',
        'leg': 'A1', 'machine': 'A1', 'out': 'A1', 'press': 'A1', 'pull': 'A1',
        'push': 'A1', 'row': 'A1', 'run': 'A1', 'side': 'A1', 'squat': 'A1',
        'stand': 'A1', 'step': 'A1', 'up': 'A1', 'walk': 'A1',
        
        'abdominal': 'A2', 'alternating': 'A2', 'assisted': 'A2', 'balance': 'A2',
        'barbell': 'A2', 'bench': 'A2', 'bent': 'A2', 'cable': 'A2', 'calf': 'A2',
        'close': 'A2', 'concentration': 'A2', 'control': 'A2', 'curl': 'A2',
        'deadlift': 'A2', 'dumbbell': 'A2', 'extension': 'A2', 'flye': 'A2',
        'goblet': 'A2', 'hammer': 'A2', 'hanging': 'A2', 'incline': 'A2',
        'kettlebell': 'A2', 'kneeling': 'A2', 'lunge': 'A2', 'neutral': 'A2',
        'overhead': 'A2', 'plank': 'A2', 'raise': 'A2', 'reverse': 'A2',
        'seated': 'A2', 'shoulder': 'A2', 'single': 'A2', 'standing': 'A2',
        'triceps': 'A2', 'weighted': 'A2', 'wide': 'A2',
        
        'abduction': 'B1', 'adduction': 'B1', 'arnold': 'B1', 'bosu': 'B1',
        'bulgarian': 'B1', 'burpee': 'B1', 'butterfly': 'B1', 'crossover': 'B1',
        'crunch': 'B1', 'decline': 'B1', 'dorsiflexion': 'B1', 'elevated': 'B1',
        'explosive': 'B1', 'external': 'B1', 'face': 'B1', 'farmers': 'B1',
        'figure': 'B1', 'flex': 'B1', 'floor': 'B1', 'flutter': 'B1',
        'hyperextension': 'B1', 'isometric': 'B1', 'jackknife': 'B1',
        'kickback': 'B1', 'kipping': 'B1', 'lateral': 'B1', 'leaning': 'B1',
        'medicine': 'B1', 'oblique': 'B1', 'offset': 'B1', 'pike': 'B1',
        'plyometric': 'B1', 'prisoner': 'B1', 'pulldown': 'B1', 'pullover': 'B1',
        'quadruped': 'B1', 'renegade': 'B1', 'retraction': 'B1', 'rotation': 'B1',
        'scaption': 'B1', 'scorpion': 'B1', 'serratus': 'B1', 'shrug': 'B1',
        'skater': 'B1', 'slam': 'B1', 'split': 'B1', 'sprint': 'B1',
        'stability': 'B1', 'staggered': 'B1', 'supine': 'B1', 'suspended': 'B1',
        'swiss': 'B1', 'thoracic': 'B1', 'thrust': 'B1', 'turkish': 'B1',
        'underhand': 'B1', 'uneven': 'B1', 'upright': 'B1', 'zercher': 'B1',
        'zottman': 'B1'
    }
    return cefr_map.get(word.lower(), 'A1')

def extract_words(text: str) -> List[str]:
    """从文本中提取所有单词并去重"""
    words = re.findall(r'\b[a-zA-Z-]+\b', text)
    unique_words = list(set(word.lower() for word in words))
    return sorted(unique_words)

def get_word_info(word: str) -> Dict:
    """从dictionaryapi.dev获取单词信息"""
    try:
        response = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}')
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                meanings = []
                for meaning in entry.get('meanings', []):
                    part_of_speech = meaning.get('partOfSpeech', '')
                    for definition in meaning.get('definitions', []):
                        meanings.append({
                            'part_of_speech': part_of_speech,
                            'definition': definition.get('definition', '')
                        })
                return {
                    'word': word,
                    'phonetic': entry.get('phonetic', ''),
                    'meanings': meanings,
                    'cefr_level': get_cefr_level(word)
                }
    except Exception as e:
        print(f"Error fetching info for {word}: {str(e)}")
    return {
        'word': word,
        'phonetic': '',
        'meanings': [],
        'cefr_level': get_cefr_level(word)
    }

def translate_text(text: str) -> str:
    """将文本翻译成中文"""
    translation_map = {
        'bench': '卧推',
        'press': '推举',
        'dumbbell': '哑铃',
        'barbell': '杠铃',
        'squat': '深蹲',
        'deadlift': '硬拉',
        'row': '划船',
        'curl': '弯举',
        'extension': '伸展',
        'raise': '上举',
        'fly': '飞鸟',
        'pull': '拉',
        'push': '推',
        'up': '上',
        'down': '下',
        'in': '内',
        'out': '外',
        'front': '前',
        'back': '后',
        'side': '侧',
        'overhead': '过头',
        'underhand': '反手',
        'wide': '宽',
        'narrow': '窄',
        'close': '窄',
        'grip': '握',
        'hold': '保持',
        'position': '姿势',
        'stance': '站姿',
        'step': '步',
        'jump': '跳',
        'walk': '走',
        'run': '跑',
        'sprint': '冲刺',
        'lunge': '弓步',
        'plank': '平板支撑',
        'crunch': '卷腹',
        'sit-up': '仰卧起坐',
        'push-up': '俯卧撑',
        'pull-up': '引体向上',
        'dip': '臂屈伸',
        'leg': '腿',
        'arm': '手臂',
        'chest': '胸部',
        'back': '背部',
        'shoulder': '肩膀',
        'core': '核心',
        'abs': '腹肌',
        'glute': '臀部',
        'calf': '小腿',
        'thigh': '大腿',
        'bicep': '二头肌',
        'tricep': '三头肌',
        'weighted': '负重',
        'bodyweight': '自重',
        'resistance': '抗阻',
        'band': '弹力带',
        'machine': '器械',
        'cable': '绳索',
        'kettlebell': '壶铃',
        'medicine': '药球',
        'ball': '球',
        'box': '箱',
        'platform': '平台',
        'rack': '架',
        'bar': '杆',
        'plate': '片'
    }
    
    words = text.lower().split()
    translated_words = [translation_map.get(word, word) for word in words]
    return ' '.join(translated_words)

def generate_pdf(word_info: List[Dict], exercise_translations: List[str], output_dir: str):
    """生成PDF文件"""
    try:
        # 生成单词词典PDF
        c = canvas.Canvas(os.path.join(output_dir, 'word_dictionary.pdf'), pagesize=letter)
        width, height = letter
        
        # 设置字体
        c.setFont("Helvetica", 12)
        
        # 添加标题
        c.drawString(100, height - 50, "Fitness Vocabulary Dictionary")
        
        # 添加内容
        y = height - 100
        for word in word_info:
            if y < 100:  # 如果接近页面底部，创建新页面
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            
            # 绘制单词和CEFR级别
            c.drawString(100, y, f"Word: {word['word']}")
            c.drawString(300, y, f"CEFR: {word['cefr_level']}")
            y -= 20
            
            # 如果有音标，使用特殊字体显示
            if word['phonetic']:
                c.drawString(100, y, f"Phonetic: {word['phonetic']}")
                y -= 20
            
            # 按词性分组显示释义
            meanings_by_pos = {}
            for meaning in word['meanings']:
                pos = meaning['part_of_speech']
                if pos not in meanings_by_pos:
                    meanings_by_pos[pos] = []
                meanings_by_pos[pos].append(meaning['definition'])
            
            for pos, definitions in meanings_by_pos.items():
                c.drawString(100, y, f"{pos}:")
                y -= 20
                for i, definition in enumerate(definitions, 1):
                    c.drawString(120, y, f"{i}. {definition}")
                    y -= 20
                y -= 10  # 词性组之间的额外间距
            
            y -= 20  # 单词之间的额外间距
        
        c.save()
        print("Successfully generated word_dictionary.pdf")
        
        # 生成动作翻译PDF
        c = canvas.Canvas(os.path.join(output_dir, 'exercise_translations.pdf'), pagesize=letter)
        width, height = letter
        
        # 设置字体
        c.setFont("Helvetica", 12)
        
        # 添加标题
        c.drawString(100, height - 50, "Exercise Translations")
        
        # 添加内容
        y = height - 100
        for translation in exercise_translations:
            if y < 100:  # 如果接近页面底部，创建新页面
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            
            parts = translation.split('\t')
            if len(parts) == 2:
                c.drawString(100, y, f"English: {parts[0]}")
                c.drawString(100, y - 20, f"Chinese: {parts[1]}")
            y -= 40
        
        c.save()
        print("Successfully generated exercise_translations.pdf")
        
    except Exception as e:
        print(f"Error generating PDF files: {str(e)}")
        raise

def generate_epub(word_info: List[Dict], exercise_translations: List[str], output_dir: str):
    """生成EPUB文件"""
    try:
        # 创建EPUB书籍
        book = epub.EpubBook()
        book.set_identifier('fitness_vocabulary')
        book.set_title('Fitness Vocabulary and Exercise Translations')
        book.set_language('en')
        
        # 创建目录
        book.toc = []
        book.spine = ['nav']
        
        # 添加单词词典章节
        word_content = '<h1>Fitness Vocabulary Dictionary</h1>'
        for word in word_info:
            word_content += f'<h2>{word["word"]}</h2>'
            word_content += f'<p>CEFR Level: {word["cefr_level"]}</p>'
            if word['phonetic']:
                word_content += f'<p>Phonetic: {word["phonetic"]}</p>'
            
            # 按词性分组显示释义
            meanings_by_pos = {}
            for meaning in word['meanings']:
                pos = meaning['part_of_speech']
                if pos not in meanings_by_pos:
                    meanings_by_pos[pos] = []
                meanings_by_pos[pos].append(meaning['definition'])
            
            for pos, definitions in meanings_by_pos.items():
                word_content += f'<h3>{pos}</h3>'
                for i, definition in enumerate(definitions, 1):
                    word_content += f'<p>{i}. {definition}</p>'
            word_content += '<hr>'
        
        word_chapter = epub.EpubHtml(title='Vocabulary Dictionary', file_name='vocabulary.xhtml', lang='en')
        word_chapter.content = word_content
        book.add_item(word_chapter)
        book.toc.append(word_chapter)
        book.spine.append(word_chapter)
        
        # 添加动作翻译章节
        translation_content = '<h1>Exercise Translations</h1>'
        for translation in exercise_translations:
            parts = translation.split('\t')
            if len(parts) == 2:
                translation_content += f'<h2>{parts[0]}</h2>'
                translation_content += f'<p>{parts[1]}</p>'
                translation_content += '<hr>'
        
        translation_chapter = epub.EpubHtml(title='Exercise Translations', file_name='translations.xhtml', lang='en')
        translation_chapter.content = translation_content
        book.add_item(translation_chapter)
        book.toc.append(translation_chapter)
        book.spine.append(translation_chapter)
        
        # 添加导航
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 设置基本样式
        style = '''
        @namespace epub "http://www.idpf.org/2007/ops";
        body {
            font-family: Arial, sans-serif;
            margin: 2em;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        h2 {
            color: #444;
            margin-top: 1.5em;
        }
        h3 {
            color: #555;
            margin-top: 1em;
        }
        p {
            margin: 0.5em 0;
        }
        hr {
            margin: 2em 0;
            border: none;
            border-top: 1px solid #ddd;
        }
        '''
        
        # 添加样式
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)
        
        # 保存EPUB文件
        epub.write_epub(os.path.join(output_dir, 'fitness_vocabulary.epub'), book, {})
        print("Successfully generated fitness_vocabulary.epub")
        
    except Exception as e:
        print(f"Error generating EPUB file: {str(e)}")
        raise

def process_file(input_file: str, output_dir: str):
    """处理输入文件并生成输出文件"""
    print(f"Processing file: {input_file}")
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Successfully read input file: {input_file}")
    except Exception as e:
        print(f"Error reading input file: {str(e)}")
        return
    
    words = extract_words(content)
    print(f"Extracted {len(words)} unique words")
    
    word_info = []
    for i, word in enumerate(words, 1):
        print(f"Processing word {i}/{len(words)}: {word}")
        info = get_word_info(word)
        word_info.append(info)
    
    # 保存单词词典
    word_dict_file = os.path.join(output_dir, 'word_dictionary.json')
    try:
        with open(word_dict_file, 'w', encoding='utf-8') as f:
            json.dump(word_info, f, ensure_ascii=False, indent=2)
        print(f"Saved word dictionary to: {word_dict_file}")
    except Exception as e:
        print(f"Error saving word dictionary: {str(e)}")
    
    # 处理动作名称
    exercise_translations = []
    for line in content.split('\n'):
        if line.strip():
            parts = line.split(',')
            if len(parts) >= 2:
                exercise_name = parts[1].strip()
                chinese_translation = translate_text(exercise_name)
                exercise_translations.append(f"{exercise_name}\t{chinese_translation}")
    
    # 保存动作翻译
    translation_file = os.path.join(output_dir, 'exercise_translations.txt')
    try:
        with open(translation_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(exercise_translations))
        print(f"Saved exercise translations to: {translation_file}")
    except Exception as e:
        print(f"Error saving exercise translations: {str(e)}")
    
    # 生成PDF和EPUB文件
    try:
        generate_pdf(word_info, exercise_translations, output_dir)
        generate_epub(word_info, exercise_translations, output_dir)
    except Exception as e:
        print(f"Error generating PDF/EPUB files: {str(e)}")

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, 'names.txt')  # 使用完整的names.txt文件
    output_dir = os.path.join(current_dir, 'translations')
    
    print(f"Current directory: {current_dir}")
    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    
    process_file(input_file, output_dir)

if __name__ == '__main__':
    main() 