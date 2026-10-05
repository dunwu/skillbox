"""
通用 Anki 卡片生成脚本（优化版）
从面试题库索引文件中提取未掌握题目，匹配源文件答案，生成 AnkiDroid 可导入的 CSV。

优化点：
- 正面：分类徽章 + 难度色标
- 代码块：保留换行、左侧色条、等宽字体
- 表格：斑马纹、圆角、表头强调
- 引用块（> 和 ::: tip）：转为彩色提示框
- 加粗文字：浅色强调
- 段落间距：自适应间距，避免拥挤
- 背面内容：仅保留 关键结论、记忆卡片、核心知识 三模块
"""

import re
import os
import sys
import glob


# === 配色方案 ===
COLORS = {
    # 背景色
    'bg_code': '#1e1e2e',       # 代码块背景（深蓝灰）
    'bg_inline': '#313244',     # 行内代码背景
    'bg_table_header': '#313244',  # 表头背景
    'bg_table_alt': '#262637',   # 表格交替行
    'bg_quote': '#1a1a2e',      # 引用块背景
    'bg_tip': '#1a2e1a',        # tip 提示框背景
    'bg_badge': '#313244',       # 徽章背景
    # 文字色
    'fg_text': '#cdd6f4',       # 主文字
    'fg_code': '#f9e2af',       # 代码块文字（淡黄）
    'fg_inline': '#f38ba8',     # 行内代码文字（粉红）
    'fg_bold': '#89b4fa',       # 加粗文字（淡蓝）
    'fg_header': '#cba6f7',     # 标题文字（淡紫）
    'fg_quote': '#a6e3a1',      # 引用块文字（淡绿）
    'fg_tip': '#a6e3a1',        # tip 文字（淡绿）
    'fg_link': '#89b4fa',       # 链接文字
    'fg_badge': '#cdd6f4',      # 徽章文字
    # 边框色
    'border_code': '#45475a',   # 代码块左边框
    'border_table': '#45475a',  # 表格边框
    'border_quote': '#a6e3a1',  # 引用块左边框
    'border_tip': '#a6e3a1',    # tip 左边框
    # 难度色
    'diff_easy': '#a6e3a1',     # 简单：绿
    'diff_medium': '#f9e2af',   # 中等：黄
    'diff_hard': '#f38ba8',     # 困难：红
}


def c(key):
    """获取配色"""
    return COLORS.get(key, '#cdd6f4')


def diff_color(diff):
    """根据难度获取颜色"""
    if '简单' in diff:
        return c('diff_easy')
    elif '困难' in diff:
        return c('diff_hard')
    else:
        return c('diff_medium')


# === HTML 转换 ===

def md_to_html(text):
    """将 Markdown 文本转为 AnkiDroid 深色主题友好的纯 HTML"""
    lines = text.split('\n')
    result = []
    i = 0
    prev_type = None  # 追踪上一行类型，用于间距控制

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- VuePress 容器 (::: tip / ::: warning 等) ---
        m = re.match(r'^:::\s*(\w+)\s*(.*)', stripped)
        if m:
            container_type = m.group(1).lower()
            container_title = m.group(2).strip()
            container_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(':::'):
                container_lines.append(lines[i])
                i += 1
            i += 1  # 跳过结束 :::
            result.append(convert_container(container_type, container_title, container_lines))
            prev_type = 'container'
            continue

        # --- 引用块 (> ...) ---
        if stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(re.sub(r'^>\s?', '', lines[i].strip()))
                i += 1
            result.append(convert_quote(quote_lines))
            prev_type = 'quote'
            continue

        # --- 代码块 ---
        if stripped.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            result.append(convert_code_block(code_lines))
            prev_type = 'code'
            continue

        # --- 表格 ---
        if stripped.startswith('|') and '|' in stripped[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            result.append(convert_table(table_lines))
            prev_type = 'table'
            continue

        # --- 图片（跳过，无法在 AnkiDroid 离线显示） ---
        if stripped.startswith('![') and '](' in stripped:
            i += 1
            continue

        # --- 标题 ---
        m = re.match(r'^(#{1,5})\s+(.+)$', stripped)
        if m:
            level = len(m.group(1))
            content = inline_format(m.group(2))
            result.append(
                f'<div style="margin:12px 0 6px 0;padding-left:8px;'
                f'border-left:3px solid {c("fg_header")};'
                f'color:{c("fg_header")};font-weight:bold;font-size:1.05em">'
                f'{content}</div>'
            )
            prev_type = 'header'
            i += 1
            continue

        # --- 无序列表 ---
        m = re.match(r'^([-*])\s+(.+)$', stripped)
        if m:
            indent = len(line) - len(line.lstrip())
            content = inline_format(m.group(2))
            margin_left = 8 + indent * 2
            result.append(
                f'<div style="margin:2px 0 2px {margin_left}px;">'
                f'<span style="color:{c("fg_bold")};font-weight:bold">•</span> {content}</div>'
            )
            prev_type = 'list'
            i += 1
            continue

        # --- 有序列表 ---
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            content = inline_format(m.group(2))
            result.append(
                f'<div style="margin:2px 0 2px 8px;">'
                f'<span style="color:{c("fg_bold")};font-weight:bold">{m.group(1)}.</span> {content}</div>'
            )
            prev_type = 'list'
            i += 1
            continue

        # --- 空行 ---
        if stripped == '':
            if prev_type and prev_type != 'spacer':
                result.append('<div style="height:6px"></div>')
                prev_type = 'spacer'
            i += 1
            continue

        # --- 普通段落 ---
        content = inline_format(stripped)
        result.append(f'<div style="margin:4px 0">{content}</div>')
        prev_type = 'paragraph'
        i += 1

    return '<br>'.join(result)


def inline_format(text):
    """处理行内格式"""
    # 转义 HTML 特殊字符（但保留已处理的标签）
    # 先处理链接 [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f'<a href="{m.group(2)}" style="color:{c("fg_link")};text-decoration:none">{inline_format(m.group(1))}</a>',
        text
    )
    # 加粗 **text**
    text = re.sub(
        r'\*\*(.+?)\*\*',
        lambda m: f'<b style="color:{c("fg_bold")}">{m.group(1)}</b>',
        text
    )
    # 行内代码 `code`
    text = re.sub(
        r'`([^`]+)`',
        lambda m: f'<code style="background:{c("bg_inline")};color:{c("fg_inline")};padding:1px 5px;border-radius:3px;font-size:0.92em">{m.group(1)}</code>',
        text
    )
    # 斜体 *text*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text


def convert_code_block(code_lines):
    """转换代码块"""
    code_content = '\n'.join(code_lines)
    code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 将换行转为 <br>，避免 CSV 单行化时被替换为空格
    code_content = code_content.replace('\n', '<br>')
    return (
        f'<pre style="background:{c("bg_code")};color:{c("fg_code")};'
        f'padding:10px 12px;border-radius:6px;overflow-x:auto;'
        f'font-size:0.88em;line-height:1.5;'
        f'border-left:3px solid {c("border_code")};'
        f'margin:8px 0;text-align:left">'
        f'<code>{code_content}</code></pre>'
    )


def convert_table(table_lines):
    """转换表格（带斑马纹）"""
    if len(table_lines) < 2:
        return '<br>'.join(table_lines)

    html = [f'<table style="border-collapse:collapse;width:100%;margin:8px 0;font-size:0.9em;border-radius:4px;overflow:hidden">']

    data_rows = []  # (is_header, cells)
    for line in table_lines:
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        is_header = (len(data_rows) == 0)
        data_rows.append((is_header, cells))

    for row_idx, (is_header, cells) in enumerate(data_rows):
        tag = 'th' if is_header else 'td'
        html.append('<tr>')
        for cell in cells:
            cell_html = inline_format(cell)
            if is_header:
                html.append(
                    f'<{tag} style="border:1px solid {c("border_table")};'
                    f'padding:6px 10px;background:{c("bg_table_header")};'
                    f'color:{c("fg_text")};text-align:left;font-weight:bold">{cell_html}</{tag}>'
                )
            else:
                # 斑马纹
                bg = c('bg_table_alt') if row_idx % 2 == 0 else 'transparent'
                html.append(
                    f'<{tag} style="border:1px solid {c("border_table")};'
                    f'padding:6px 10px;background:{bg};'
                    f'color:{c("fg_text")};text-align:left">{cell_html}</{tag}>'
                )
        html.append('</tr>')

    html.append('</table>')
    return ''.join(html)


def convert_quote(quote_lines):
    """转换引用块（> 语法）为提示框"""
    content = ' '.join(quote_lines)
    content = inline_format(content)
    return (
        f'<div style="background:{c("bg_quote")};'
        f'border-left:3px solid {c("border_quote")};'
        f'padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;'
        f'color:{c("fg_quote")};font-size:0.95em;text-align:left">{content}</div>'
    )


def convert_container(container_type, title, content_lines):
    """转换 VuePress 容器 (::: tip 等) 为提示框"""
    content = ' '.join([l.strip() for l in content_lines if l.strip()])
    content = inline_format(content)

    type_config = {
        'tip': ('#a6e3a1', '#1a2e1a'),
        'warning': ('#f9e2af', '#2e2a1a'),
        'danger': ('#f38ba8', '#2e1a1a'),
        'info': ('#89b4fa', '#1a1a2e'),
        'details': ('#cba6f7', '#2a1a2e'),
    }

    border_color, bg_color = type_config.get(container_type, type_config['tip'])
    title_html = ''
    if title:
        title_html = f'<b style="color:{border_color}">{title}</b><br>'

    return (
        f'<div style="background:{bg_color};'
        f'border-left:3px solid {border_color};'
        f'padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;'
        f'color:{c("fg_text")};font-size:0.95em;text-align:left">'
        f'{title_html}{content}</div>'
    )


# === 正面卡片生成 ===

def build_front(cat, title, diff, stars):
    """生成正面卡片 HTML"""
    dc = diff_color(diff)
    return (
        f'<div style="text-align:left">'
        f'<span style="background:{c("bg_badge")};color:{c("fg_badge")};'
        f'padding:2px 8px;border-radius:4px;font-size:0.85em">{cat}</span>'
        f' <span style="color:{dc};font-size:0.85em">[{diff}]</span>'
        f'<div style="margin-top:8px;font-size:1.1em;font-weight:bold">{title}</div>'
        f'</div>'
    )


# === 背面内容模块截取 ===

# 卡片背面仅保留这三个模块（按模板标题中的中文名匹配，避免 emoji 编码差异）
KEEP_MODULES = ('关键结论', '记忆卡片', '核心知识')


def filter_answer_modules(body):
    """只保留 关键结论/记忆卡片/核心知识 三个模块，返回 (filtered_body, missing_names)"""
    parts = re.split(r'(?m)^(#### .+)$', body)
    if len(parts) < 3:
        # 旧格式答案无模块标题：回退为全文导出，不报缺失
        return body.strip(), []
    kept = []
    found = set()
    for i in range(1, len(parts), 2):
        heading = parts[i]
        section = parts[i + 1] if i + 1 < len(parts) else ''
        for name in KEEP_MODULES:
            if name in heading:
                kept.append(heading + section)
                found.add(name)
                break
    missing = [name for name in KEEP_MODULES if name not in found]
    return ''.join(kept).strip(), missing


# === 题库处理 ===

def extract_questions(index_path):
    """从题库索引文件中提取所有题目及其掌握度"""
    questions = []
    with open(index_path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s.startswith('|') or '---' in s or '分类' in s:
                continue
            parts = [p.strip() for p in s.split('|')[1:-1]]
            if len(parts) >= 6:
                questions.append({
                    'cat': parts[0],
                    'title': parts[1],
                    'diff': parts[2],
                    'stars': parts[3],
                    'mastery': parts[4]
                })
    return questions


def extract_qa_from_sources(source_dir):
    """从源文件中提取所有 Q&A"""
    qa_map = {}
    files = sorted(glob.glob(os.path.join(source_dir, '*.md')))
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        sections = re.split(r'^(### .+)$', content, flags=re.MULTILINE)
        for i in range(1, len(sections) - 1, 2):
            heading = sections[i].strip()
            body = sections[i + 1].strip()
            m = re.match(r'### [【\[]?(简单|中等|困难)[】\]]?\s*(.+)', heading)
            if m:
                title = m.group(2).strip()
                title = re.sub(r'\s*⭐+\s*$', '', title).strip()
                qa_map[title] = body
    return qa_map


def filter_by_mastery(questions, mastery_filter=None):
    if mastery_filter is None:
        mastery_filter = {'\u26a0\ufe0f', '\u274c'}
    return [q for q in questions if q['mastery'] in mastery_filter]


# === 主流程 ===

def main():
    index_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('docs', '99.面试', 'JavaCore面试.md')
    source_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join('docs', '01.Java', 'JavaCore', '面试')
    output_path = sys.argv[3] if len(sys.argv) > 3 else 'anki_cards.csv'

    mastery_env = os.environ.get('ANKI_MASTERY', '')
    if mastery_env:
        mastery_filter = set()
        if 'warning' in mastery_env:
            mastery_filter.add('\u26a0\ufe0f')
        if 'failed' in mastery_env:
            mastery_filter.add('\u274c')
        if 'empty' in mastery_env:
            mastery_filter.add('')
    else:
        mastery_filter = None

    print(f'题库索引：{index_path}')
    print(f'源文件目录：{source_dir}')
    print(f'输出文件：{output_path}')

    print('\n步骤 1：提取题目...')
    all_questions = extract_questions(index_path)
    print(f'  总题数：{len(all_questions)}')
    filtered = filter_by_mastery(all_questions, mastery_filter)
    print(f'  筛选后：{len(filtered)} 道')

    print('\n步骤 2：提取源文件答案...')
    qa_map = extract_qa_from_sources(source_dir)
    print(f'  源文件 Q&A：{len(qa_map)} 道')

    print('\n步骤 3：匹配答案并生成卡片...')
    cards = []
    unmatched = []
    missing_modules = []
    for q in filtered:
        title = q['title']
        if title in qa_map:
            body, missing = filter_answer_modules(qa_map[title])
            if missing:
                missing_modules.append(title + '（缺：' + '、'.join(missing) + '）')
            answer_html = md_to_html(body)
            front = build_front(q['cat'], title, q['diff'], q['stars'])
            back = f'<div style="text-align:left;line-height:1.6;font-size:0.95em">{answer_html}</div>'
            cards.append((front, back))
        else:
            unmatched.append(title)

    print(f'  成功匹配：{len(cards)} 道')
    if unmatched:
        print(f'  未匹配：{len(unmatched)} 道')
        for t in unmatched:
            print(f'    - {t}')
    if missing_modules:
        print(f'  模块缺失：{len(missing_modules)} 道（背面仅导出存在的模块）')
        for t in missing_modules:
            print(f'    - {t}')

    with open(output_path, 'w', encoding='utf-8-sig') as f:
        for front, back in cards:
            front = front.replace('\t', ' ').replace('\n', ' ').replace('\r', '')
            back = back.replace('\t', ' ').replace('\n', ' ').replace('\r', '')
            f.write(f'{front}\t{back}\n')

    print(f'\n完成！共 {len(cards)} 张卡片 → {output_path}')
    print('AnkiDroid 导入：分隔符选 Tab，勾选"允许 HTML"')


if __name__ == '__main__':
    main()
