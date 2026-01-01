# -*- coding: utf-8 -*-
"""
📄 PDF 생성기 v2 - 150페이지 프리미엄 보고서
- David님 서식 적용
- 이미지 태그 {{IMG:xx_표이름}} 자동 삽입
- 표지, 목차, 본문, 페이지 번호
"""

import os
import re
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image


# ============================================
# 서식 설정 (David님 지침)
# ============================================
PAGE_WIDTH, PAGE_HEIGHT = A4

# 여백 (25mm)
MARGIN_TOP = 25 * mm
MARGIN_BOTTOM = 25 * mm
MARGIN_LEFT = 25 * mm
MARGIN_RIGHT = 25 * mm

# 글자 크기
TITLE_SIZE = 30  # 대주제 (장 제목)
SUBTITLE_SIZE = 25  # 소주제
BODY_SIZE = 17  # 본문

# 줄간격 120%
LINE_HEIGHT_RATIO = 1.2
BODY_LINE_HEIGHT = BODY_SIZE * LINE_HEIGHT_RATIO
SUBTITLE_LINE_HEIGHT = SUBTITLE_SIZE * LINE_HEIGHT_RATIO

# 본문 영역
TEXT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
TEXT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM


# ============================================
# 폰트 설정
# ============================================
FONT_NAME = 'NanumBarunGothic'
FONT_BOLD = 'NanumBarunGothicBold'
FONT_LOADED = False


def setup_fonts(fonts_dir=None):
    """한글 폰트 설정"""
    global FONT_NAME, FONT_BOLD, FONT_LOADED
    
    if FONT_LOADED:
        return FONT_NAME, FONT_BOLD
    
    # 폰트 검색 경로
    font_paths = []
    
    if fonts_dir and os.path.exists(fonts_dir):
        font_paths.extend([
            os.path.join(fonts_dir, f) for f in os.listdir(fonts_dir) if f.endswith('.ttf')
        ])
    
    # 시스템 폰트
    font_paths.extend([
        'C:/Windows/Fonts/NanumBarunGothic.ttf',
        'C:/Windows/Fonts/NanumGothic.ttf',
        'C:/Windows/Fonts/malgun.ttf',
        '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    ])
    
    # ChosunGs (기존 프로젝트용)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_paths.append(os.path.join(script_dir, 'fonts', 'ChosunGs.TTF'))
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', path))
                pdfmetrics.registerFont(TTFont('KoreanBold', path))
                FONT_NAME = 'Korean'
                FONT_BOLD = 'KoreanBold'
                FONT_LOADED = True
                return FONT_NAME, FONT_BOLD
            except:
                continue
    
    return 'Helvetica', 'Helvetica-Bold'


# ============================================
# 이미지 태그 처리
# ============================================
IMG_TAG_PATTERN = re.compile(r'\{\{IMG:([^}]+)\}\}')


def find_image(tag_name, images_dir):
    """이미지 태그에 해당하는 파일 찾기"""
    if not images_dir or not os.path.exists(images_dir):
        return None
    
    for filename in os.listdir(images_dir):
        # 태그명이 파일명에 포함되어 있으면 매칭
        base_name = os.path.splitext(filename)[0]
        if tag_name == filename or tag_name == base_name or tag_name in filename:
            return os.path.join(images_dir, filename)
    
    return None


# ============================================
# 텍스트 줄바꿈
# ============================================
def wrap_text(text, font_name, font_size, max_width, c):
    """텍스트를 최대 너비에 맞게 줄바꿈"""
    lines = []
    
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        
        line = ''
        for char in paragraph:
            test_line = line + char
            if c.stringWidth(test_line, font_name, font_size) <= max_width:
                line = test_line
            else:
                if line:
                    lines.append(line)
                line = char
        
        if line:
            lines.append(line)
    
    return lines


# ============================================
# PDF 생성 메인
# ============================================
def create_full_pdf(chapters, images_dir, customer_name, output_path, 기본정보=None):
    """
    전체 PDF 생성
    
    Args:
        chapters: {1: "제1장 내용...", 2: "제2장 내용...", ...}
        images_dir: 이미지 폴더 경로
        customer_name: 고객 이름
        output_path: PDF 저장 경로
        기본정보: {'이름', '성별', '나이', '양력', '음력'}
    """
    font_name, font_bold = setup_fonts()
    
    c = canvas.Canvas(output_path, pagesize=A4)
    page_num = 0
    
    def new_page():
        """새 페이지 시작"""
        nonlocal page_num
        if page_num > 0:
            # 페이지 번호 (하단 중앙)
            c.setFont(font_name, 10)
            c.drawCentredString(PAGE_WIDTH / 2, MARGIN_BOTTOM - 10 * mm, str(page_num))
            c.showPage()
        page_num += 1
        return PAGE_HEIGHT - MARGIN_TOP
    
    # ============================================
    # 표지
    # ============================================
    y = new_page()
    
    # 제목
    c.setFont(font_bold, 40)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT * 0.6, "사주 분석 보고서")
    
    # 고객명
    c.setFont(font_name, 28)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT * 0.45, f"{customer_name} 님")
    
    # 기본정보
    if 기본정보:
        c.setFont(font_name, 14)
        info_y = PAGE_HEIGHT * 0.35
        c.drawCentredString(PAGE_WIDTH / 2, info_y, f"양력: {기본정보.get('양력', '')}")
        c.drawCentredString(PAGE_WIDTH / 2, info_y - 20, f"음력: {기본정보.get('음력', '')}")
    
    # 생성일
    from datetime import datetime
    c.setFont(font_name, 12)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT * 0.15, f"생성일: {datetime.now().strftime('%Y년 %m월 %d일')}")
    
    # ============================================
    # 목차
    # ============================================
    y = new_page()
    
    c.setFont(font_bold, TITLE_SIZE)
    c.drawCentredString(PAGE_WIDTH / 2, y, "목 차")
    y -= 50
    
    c.setFont(font_name, 14)
    
    chapter_titles = {
        1: "일년 운세 리포트의 해석 관점",
        2: "사주 구조 핵심 요약",
        3: "일년 전체 운의 큰 흐름",
        4: "상반기 월별 운의 작동 구조",
        5: "하반기 월별 운의 변화 포인트",
        6: "감정·심리 흐름",
        7: "인간관계 전반의 운 흐름",
        8: "연애·부부·이성 운",
        9: "직업·일·커리어 운",
        10: "재물·수입·지출 운",
        11: "건강·에너지 흐름",
        12: "선택이 중요한 시점들",
        13: "조심해야 할 작용",
        14: "해 운을 활용하는 전략",
        15: "이 한 해가 남기는 의미",
    }
    
    for ch_num in range(1, 16):
        title = chapter_titles.get(ch_num, "")
        c.drawString(MARGIN_LEFT + 20, y, f"제{ch_num}장. {title}")
        y -= 25
        
        if y < MARGIN_BOTTOM + 50:
            y = new_page()
            c.setFont(font_name, 14)
    
    # ============================================
    # 본문 (장별)
    # ============================================
    used_images = set()
    
    for ch_num in sorted(chapters.keys()):
        content = chapters[ch_num]
        ch_title = chapter_titles.get(ch_num, "")
        
        # 장 제목 페이지
        y = new_page()
        
        c.setFont(font_bold, TITLE_SIZE)
        c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT * 0.55, f"제{ch_num}장")
        c.setFont(font_name, SUBTITLE_SIZE)
        c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT * 0.55 - 45, ch_title)
        
        # 본문 시작
        y = new_page()
        
        # 내용 파싱 및 렌더링
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                y -= BODY_LINE_HEIGHT * 0.5
                continue
            
            # 이미지 태그 확인
            img_match = IMG_TAG_PATTERN.search(line)
            if img_match:
                tag_name = img_match.group(1)
                img_path = find_image(tag_name, images_dir)
                
                if img_path and img_path not in used_images:
                    # 이미지 삽입
                    try:
                        pil_img = Image.open(img_path)
                        img_w, img_h = pil_img.size
                        
                        # 최대 크기 제한
                        max_img_width = TEXT_WIDTH * 0.9
                        max_img_height = PAGE_HEIGHT * 0.4
                        
                        scale = min(max_img_width / img_w, max_img_height / img_h, 1)
                        new_w = img_w * scale
                        new_h = img_h * scale
                        
                        # 페이지 넘김 확인
                        if y - new_h < MARGIN_BOTTOM + 50:
                            y = new_page()
                        
                        img_x = (PAGE_WIDTH - new_w) / 2
                        img_y = y - new_h
                        
                        c.drawImage(
                            ImageReader(img_path),
                            img_x, img_y,
                            width=new_w, height=new_h,
                            mask='auto'
                        )
                        
                        used_images.add(img_path)
                        y = img_y - BODY_LINE_HEIGHT * 2
                        
                    except Exception as e:
                        print(f"[경고] 이미지 삽입 실패: {tag_name} - {e}")
                
                continue
            
            # 소주제 판단 (숫자. 으로 시작하거나 특정 기호)
            is_subtitle = False
            if re.match(r'^\d+\.', line):
                is_subtitle = True
            elif any(line.startswith(c) for c in ['▶', '●', '◆', '★', '■']):
                is_subtitle = True
            
            if is_subtitle:
                # 소주제
                c.setFont(font_bold, SUBTITLE_SIZE)
                
                wrapped = wrap_text(line, font_bold, SUBTITLE_SIZE, TEXT_WIDTH, c)
                
                needed_height = len(wrapped) * SUBTITLE_LINE_HEIGHT + 20
                if y - needed_height < MARGIN_BOTTOM + 30:
                    y = new_page()
                    c.setFont(font_bold, SUBTITLE_SIZE)
                
                y -= 15  # 소주제 전 여백
                
                for wline in wrapped:
                    c.drawString(MARGIN_LEFT, y, wline)
                    y -= SUBTITLE_LINE_HEIGHT
                
                y -= 10  # 소주제 후 여백
                
            else:
                # 본문
                c.setFont(font_name, BODY_SIZE)
                
                wrapped = wrap_text(line, font_name, BODY_SIZE, TEXT_WIDTH, c)
                
                for wline in wrapped:
                    if y < MARGIN_BOTTOM + 30:
                        y = new_page()
                        c.setFont(font_name, BODY_SIZE)
                    
                    c.drawString(MARGIN_LEFT, y, wline)
                    y -= BODY_LINE_HEIGHT
    
    # 마지막 페이지 번호
    c.setFont(font_name, 10)
    c.drawCentredString(PAGE_WIDTH / 2, MARGIN_BOTTOM - 10 * mm, str(page_num))
    
    c.save()
    
    print(f"✅ PDF 생성 완료: {output_path} ({page_num}페이지)")
    return output_path


# ============================================
# 테스트
# ============================================
if __name__ == "__main__":
    print("PDF Generator v2 로드 완료")
    print(f"페이지 크기: {PAGE_WIDTH/mm:.0f}mm x {PAGE_HEIGHT/mm:.0f}mm")
    print(f"여백: {MARGIN_LEFT/mm:.0f}mm")
