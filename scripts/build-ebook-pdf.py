"""전자책 MD → KDP 출판용 PDF 변환
'월요일이 기다려지는 사람들의 비밀' — 류선희 저"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, re
from fpdf import FPDF

HOME = os.path.expanduser("~")
PRODUCT_DIR = os.path.join(HOME, "lighthouse-media", "products", "ebook-monday-recovery")
OUTPUT_DIR = os.path.join(HOME, "lighthouse-biz", "ebooks")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 50)
print("  전자책 PDF 빌드")
print("  월요일이 기다려지는 사람들의 비밀")
print("=" * 50)

# 1. MD 파일 로딩
print("\n[1/3] 마크다운 로딩...")
parts = []
file_order = [
    '00-prologue.md',
    '02-part1.md',    # Ch 1-2
    '02-part1b.md',   # Ch 3-5
    '02-part2.md',    # Ch 6-7
    '02-part2b.md',   # Ch 8-10
    '03-appendix.md', # 부록 + 에필로그
]
for fname in file_order:
    fpath = os.path.join(PRODUCT_DIR, fname)
    if os.path.exists(fpath):
        content = open(fpath, encoding='utf-8').read()
        parts.append(content)
        print(f"  ✓ {fname} ({len(content):,} bytes)")

full_md = '\n\n'.join(parts)
print(f"  총 {len(full_md):,} bytes")

# 2. PDF 생성
print("\n[2/3] PDF 생성...")

pdf = FPDF(format='A4')  # A4 210x297mm — 넉넉한 공간
pdf.add_font('malgun', '', 'C:/Windows/Fonts/malgun.ttf')
pdf.add_font('malgun', 'B', 'C:/Windows/Fonts/malgunbd.ttf')
pdf.set_auto_page_break(auto=True, margin=25)
pdf.set_left_margin(25)
pdf.set_right_margin(25)

def clean_md(text):
    """마크다운 강조 제거"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    return text.strip()

def safe_cell(pdf, w, h, text, **kwargs):
    """긴 텍스트 안전하게 출력"""
    try:
        pdf.multi_cell(w, h, text, **kwargs)
    except Exception:
        # 너무 긴 줄은 분리해서 출력
        words = text.split(' ')
        line = ''
        for word in words:
            test = line + ' ' + word if line else word
            if len(test) > 60:
                if line:
                    pdf.multi_cell(w, h, line, **kwargs)
                line = word
            else:
                line = test
        if line:
            pdf.multi_cell(w, h, line, **kwargs)

# --- 표지 ---
pdf.add_page()
pdf.ln(60)
pdf.set_font('malgun', 'B', 28)
pdf.set_text_color(27, 42, 74)
pdf.cell(0, 14, '월요일이 기다려지는', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 14, '사람들의 비밀', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(10)
pdf.set_font('malgun', '', 14)
pdf.set_text_color(90, 90, 90)
pdf.cell(0, 9, '번아웃 없이 일하는 직장인의', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.cell(0, 9, '마인드셋과 루틴', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(25)
pdf.set_font('malgun', '', 13)
pdf.set_text_color(70, 70, 70)
pdf.cell(0, 9, '류선희 저', align='C', new_x='LMARGIN', new_y='NEXT')
pdf.ln(5)
pdf.set_font('malgun', '', 10)
pdf.set_text_color(186, 117, 23)
pdf.cell(0, 9, 'Lighthouse Media', align='C', new_x='LMARGIN', new_y='NEXT')

# --- 저작권 ---
pdf.add_page()
pdf.ln(150)
pdf.set_font('malgun', '', 8)
pdf.set_text_color(130, 130, 130)
for line in [
    '월요일이 기다려지는 사람들의 비밀',
    '번아웃 없이 일하는 직장인의 마인드셋과 루틴',
    '', '저자: 류선희', '출판: Lighthouse Media', '초판 발행: 2026년 6월',
    '', '이 책의 저작권은 저자에게 있습니다.', '무단 전재 및 복제를 금합니다.',
    '', '(c) 2026 류선희 / Lighthouse Media', 'Instagram: @lighthouse_media77',
]:
    pdf.cell(0, 5, line, align='C', new_x='LMARGIN', new_y='NEXT')

# --- 본문 ---
lines = full_md.split('\n')
page_started = False
for line in lines:
    stripped = line.strip()
    if not stripped:
        continue

    # Chapter title
    if stripped.startswith('# '):
        title = clean_md(stripped[2:])
        pdf.add_page()
        pdf.ln(20)
        pdf.set_font('malgun', 'B', 20)
        pdf.set_text_color(27, 42, 74)
        safe_cell(pdf, 0, 11, title)
        pdf.ln(8)
        continue

    # Subtitle
    if stripped.startswith('## '):
        text = clean_md(stripped[3:])
        pdf.set_font('malgun', 'B', 12)
        pdf.set_text_color(44, 62, 107)
        safe_cell(pdf, 0, 8, text)
        pdf.ln(5)
        continue

    # Section
    if stripped.startswith('### '):
        text = clean_md(stripped[4:])
        pdf.ln(3)
        pdf.set_font('malgun', 'B', 11)
        pdf.set_text_color(74, 85, 104)
        safe_cell(pdf, 0, 7, text)
        pdf.ln(3)
        continue

    # Separator
    if stripped.startswith('---'):
        pdf.ln(5)
        continue

    # Bold paragraph
    if stripped.startswith('**') and stripped.endswith('**'):
        text = clean_md(stripped)
        pdf.ln(2)
        pdf.set_font('malgun', 'B', 10)
        pdf.set_text_color(27, 42, 74)
        safe_cell(pdf, 0, 6.5, text)
        pdf.ln(2)
        continue

    # List items
    if stripped.startswith('- ') or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in '.'):
        text = clean_md(stripped)
        pdf.set_font('malgun', '', 10)
        pdf.set_text_color(45, 45, 45)
        safe_cell(pdf, 0, 6, '  ' + text)
        pdf.ln(1)
        continue

    # Normal paragraph
    text = clean_md(stripped)
    pdf.set_font('malgun', '', 10)
    pdf.set_text_color(45, 45, 45)
    safe_cell(pdf, 0, 6.5, text)
    pdf.ln(2)

# --- 에필로그 ---
pdf.add_page()
pdf.ln(20)
pdf.set_font('malgun', 'B', 20)
pdf.set_text_color(27, 42, 74)
pdf.cell(0, 11, '에필로그', align='L', new_x='LMARGIN', new_y='NEXT')
pdf.ln(10)
pdf.set_font('malgun', '', 10)
pdf.set_text_color(45, 45, 45)
for para in [
    '이 책을 읽기 시작할 때의 당신과 지금의 당신은 분명 다릅니다. 완벽한 변화가 아니어도 괜찮습니다. 한 가지라도 새로운 시각을 얻었다면, 그것이 바로 변화의 시작입니다.',
    '월요일이 기다려지는 삶은 거창한 것이 아닙니다. 오늘 하루를 의미 있게 보내겠다는 작은 결심, 그것이 모여 당신의 삶을 바꿉니다.',
    '당신의 월요일을 응원합니다.',
]:
    safe_cell(pdf, 0, 6.5, para)
    pdf.ln(4)

pdf.ln(15)
pdf.set_font('malgun', '', 10)
pdf.cell(0, 8, '류선희 드림', align='R', new_x='LMARGIN', new_y='NEXT')
pdf.ln(30)
pdf.set_font('malgun', '', 8)
pdf.set_text_color(130, 130, 130)
pdf.cell(0, 5, '더 많은 콘텐츠: Instagram @lighthouse_media77', align='C', new_x='LMARGIN', new_y='NEXT')

# 3. 저장
print("\n[3/3] 저장...")
pdf_path = os.path.join(OUTPUT_DIR, "월요일이-기다려지는-사람들의-비밀_류선희.pdf")
pdf.output(pdf_path)

size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
print(f"\n  PDF 생성 완료!")
print(f"  파일: {pdf_path}")
print(f"  크기: {size_mb:.1f}MB")
print(f"  페이지: {pdf.page_no()}쪽")
print(f"\n  KDP 업로드 정보:")
print(f"  - 제목: 월요일이 기다려지는 사람들의 비밀")
print(f"  - 부제: 번아웃 없이 일하는 직장인의 마인드셋과 루틴")
print(f"  - 저자: 류선희")
print(f"  - 가격: $4.99 / 7,900원")
print(f"  - 카테고리: Self-Help > Stress Management")
print(f"\n{'='*50}")
print(f"  빌드 완료!")
print(f"{'='*50}")
