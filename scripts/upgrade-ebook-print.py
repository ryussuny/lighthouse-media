"""모든 전자책 HTML에 소책자 스타일 프린트 CSS 적용"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, glob, re

HOME = os.path.expanduser("~")
EBOOK_DIR = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "ebooks")

PRINT_CSS = """
  /* ══════════════════════════════════════
     소책자 스타일 PDF 인쇄 설정
     ══════════════════════════════════════ */
  @media print {
    @page {
      size: A4;
      margin: 20mm 18mm 25mm 18mm;
    }

    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }

    body {
      background: #fff !important;
      color: #222 !important;
      font-size: 11pt !important;
      line-height: 1.8 !important;
      max-width: 100% !important;
      padding: 0 !important;
      margin: 0 !important;
    }

    /* 표지: 전체 페이지 */
    .cover, section.cover {
      page-break-after: always !important;
      min-height: 100vh !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: center !important;
      align-items: center !important;
      background: linear-gradient(135deg, #1a1a2e, #16213e) !important;
      color: #fff !important;
      padding: 60px 40px !important;
    }

    /* 본문 영역 */
    .content, .body-content, main {
      padding: 0 !important;
      max-width: 100% !important;
    }

    /* 챕터 제목: 새 페이지 시작 */
    h2 {
      page-break-before: always !important;
      page-break-after: avoid !important;
      font-size: 18pt !important;
      color: #1D9E75 !important;
      margin-top: 0 !important;
      padding-top: 20px !important;
      padding-bottom: 12px !important;
      border-left: 4px solid #1D9E75 !important;
      padding-left: 14px !important;
    }

    /* 첫 번째 h2는 새 페이지 안함 (표지 바로 다음) */
    .content h2:first-of-type, .body-content h2:first-of-type {
      page-break-before: avoid !important;
    }

    h3 {
      page-break-after: avoid !important;
      font-size: 14pt !important;
      color: #333 !important;
      margin-top: 24px !important;
      margin-bottom: 8px !important;
    }

    p {
      font-size: 11pt !important;
      line-height: 1.9 !important;
      margin-bottom: 12px !important;
      color: #333 !important;
      orphans: 3 !important;
      widows: 3 !important;
      text-align: justify !important;
      word-break: keep-all !important;
    }

    /* 리스트 */
    ul, ol {
      margin: 8px 0 14px 20px !important;
      page-break-inside: avoid !important;
    }
    li {
      font-size: 11pt !important;
      line-height: 1.8 !important;
      margin-bottom: 6px !important;
    }

    /* 인용문 */
    blockquote {
      border-left: 3px solid #1D9E75 !important;
      background: #f5f5f0 !important;
      padding: 12px 16px !important;
      margin: 14px 0 !important;
      font-size: 10.5pt !important;
      page-break-inside: avoid !important;
      border-radius: 0 !important;
    }

    /* 강조 */
    strong { color: #1D9E75 !important; }
    em { color: #BA7517 !important; font-style: normal !important; }

    /* 코드/체크리스트 블록 */
    pre, code {
      background: #f0f0ea !important;
      font-size: 10pt !important;
      page-break-inside: avoid !important;
    }

    /* 테이블 */
    table {
      width: 100% !important;
      border-collapse: collapse !important;
      page-break-inside: avoid !important;
      font-size: 10pt !important;
      margin: 12px 0 !important;
    }
    th {
      background: #1D9E75 !important;
      color: #fff !important;
      padding: 8px 10px !important;
      font-weight: 600 !important;
      text-align: left !important;
    }
    td {
      padding: 8px 10px !important;
      border-bottom: 1px solid #ddd !important;
    }

    /* 페이지 하단 푸터 */
    .content::after, .body-content::after {
      content: "Lighthouse Media | 류선희 | 실제로 삶이 나아지는 콘텐츠";
      display: block;
      text-align: center;
      font-size: 8pt;
      color: #999;
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #ddd;
    }

    /* 숨길 요소들 */
    .actions, .cta, .cta-box, .btn-print, .toolbar, button,
    nav, .header-nav, .nav, .footer-cta, .follow-banner,
    .sidebar-cta, .print-bar, .no-print {
      display: none !important;
    }

    /* 이미지 */
    img {
      max-width: 100% !important;
      page-break-inside: avoid !important;
    }

    /* 링크 URL 표시 안함 */
    a { color: #1D9E75 !important; text-decoration: none !important; }
    a::after { content: none !important; }

    /* 카드/박스 스타일 */
    .tip-box, .highlight-box, .note-box, .checklist-box {
      background: #f9f9f5 !important;
      border: 1px solid #e0e0d8 !important;
      padding: 14px !important;
      margin: 12px 0 !important;
      page-break-inside: avoid !important;
      border-radius: 6px !important;
    }

    /* 구분선 */
    hr {
      border: none !important;
      border-top: 1px solid #ddd !important;
      margin: 20px 0 !important;
    }
  }

  /* 프린트 버튼 스타일 개선 */
  .print-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: rgba(250,248,243,0.97);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #eee;
    z-index: 1000;
    backdrop-filter: blur(8px);
  }
  .print-bar .brand-text { font-size: 13px; color: #999; font-weight: 600; }
  .print-bar .btn-save {
    background: #1D9E75;
    color: #fff;
    border: none;
    padding: 8px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 700;
    font-size: 13px;
    font-family: 'Pretendard', sans-serif;
  }
  .print-bar .btn-save:hover { background: #178a65; }
  .print-bar .btn-home {
    color: #999;
    text-decoration: none;
    font-size: 13px;
    padding: 8px 14px;
    border: 1px solid #eee;
    border-radius: 8px;
  }
  .print-bar .btn-home:hover { color: #1D9E75; border-color: #1D9E75; }
"""

PRINT_BAR_HTML = """
<div class="print-bar">
  <span class="brand-text">Lighthouse Media</span>
  <div style="display:flex;gap:8px;align-items:center">
    <a href="/home.html" class="btn-home">홈으로</a>
    <a href="/ebook-library.html" class="btn-home">전자책 더보기</a>
    <button class="btn-save" onclick="window.print()">PDF로 저장하기</button>
  </div>
</div>
<div style="height:50px"></div>
"""

count = 0
files = glob.glob(os.path.join(EBOOK_DIR, "**", "*.html"), recursive=True)

for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            html = f.read()
    except:
        continue

    if "index" in os.path.basename(fpath):
        continue

    modified = False

    # 1. 기존 @media print 블록 제거
    html = re.sub(r'@media\s+print\s*\{[^}]*(\{[^}]*\}[^}]*)*\}', '', html)
    modified = True

    # 2. </style> 앞에 새 프린트 CSS 삽입
    if '</style>' in html:
        html = html.replace('</style>', PRINT_CSS + '\n</style>', 1)
        modified = True

    # 3. 기존 프린트 버튼/액션 영역 교체
    # 기존 actions div 제거
    html = re.sub(r'<div class="actions">.*?</div>', '', html, flags=re.DOTALL)
    # 기존 print-bar/toolbar 제거
    html = re.sub(r'<div class="print-bar">.*?</div>\s*<div style="height:\d+px"></div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div class="toolbar">.*?</div>\s*<div style="height:\d+px"></div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<button[^>]*onclick="window\.print\(\)"[^>]*>.*?</button>', '', html, flags=re.DOTALL)

    # 4. <body> 바로 뒤에 새 프린트 바 삽입
    if '<body>' in html and 'print-bar' not in html:
        html = html.replace('<body>', '<body>\n' + PRINT_BAR_HTML, 1)
        modified = True
    elif '<body' in html and 'print-bar' not in html:
        # <body ...> 형태
        body_match = re.search(r'<body[^>]*>', html)
        if body_match:
            pos = body_match.end()
            html = html[:pos] + '\n' + PRINT_BAR_HTML + html[pos:]
            modified = True

    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(html)
        count += 1
        name = os.path.basename(fpath)
        print(f"  {name}")

print(f"\n  {count}개 전자책 업그레이드 완료!")
