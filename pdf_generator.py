# -*- coding: utf-8 -*-
"""
📄 PDF 자동 생성 모듈 (v7 기반)
- Docx + 이미지 → PDF 조립
- 표지, 목차, 본문, 안내 페이지 자동 구성
- {{IMG:태그}} 형식 이미지 삽입 지원
"""

import os
import io
import re
from typing import Dict, List, Tuple, Optional, Callable

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image


# ============================================
# 전역 폰트 변수
# ============================================
FONT_NAME = 'Helvetica'
BOLD_NAME = 'Helvetica-Bold'
FONT_LOADED = False


def setup_fonts(fonts_dir: str = None, system_fonts: List[str] = None) -> Tuple[str, str]:
    """
    한글 폰트 설정
    
    Args:
        fonts_dir: 폰트 폴더 경로 (없으면 현재 폴더/fonts)
        system_fonts: 시스템 폰트 경로 리스트
        
    Returns:
        (일반폰트명, 볼드폰트명) 튜플
    """
    global FONT_NAME, BOLD_NAME, FONT_LOADED
    
    if FONT_LOADED:
        return FONT_NAME, BOLD_NAME
    
    # 기본 fonts 폴더
    if fonts_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(script_dir, 'fonts')
    
    # 폰트 파일 수집
    font_files = []
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith('.ttf'):
                font_files.append(os.path.join(fonts_dir, f))
    
    # 시스템 폰트
    if system_fonts is None:
        system_fonts = [
            'C:/Windows/Fonts/NanumGothic.ttf',
            'C:/Windows/Fonts/malgun.ttf',
            '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        ]
    
    all_fonts = font_files + system_fonts
    
    for path in all_fonts:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', path))
                pdfmetrics.registerFont(TTFont('KoreanBold', path))
                FONT_NAME = 'Korean'
                BOLD_NAME = 'KoreanBold'
                FONT_LOADED = True
                return FONT_NAME, BOLD_NAME
            except Exception:
                continue
    
    return FONT_NAME, BOLD_NAME


def read_docx(file_path_or_buffer) -> List[Dict]:
    """
    Docx 파일 읽기
    
    Args:
        file_path_or_buffer: 파일 경로 또는 BytesIO
        
    Returns:
        [{"text": str, "style": str}, ...] 리스트
    """
    try:
        doc = Document(file_path_or_buffer)
        content = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                style = para.style.name if para.style else "Normal"
                content.append({"text": text, "style": style})
        return content
    except Exception as e:
        return []


def classify_images(images: Dict[str, bytes]) -> Dict:
    """
    이미지 분류 (표지, 내지, 장배경, 목차, 안내, 사주표)
    
    Args:
        images: {파일명: 바이트데이터} 딕셔너리
        
    Returns:
        분류된 이미지 딕셔너리
    """
    result = {
        'cover': None,          # 표지
        'page_bg': None,        # 내지 배경
        'chapter_bg': None,     # 장 배경
        'toc': [],              # 목차 [(이름, 데이터), ...]
        'guide': [],            # 안내 [(이름, 데이터), ...]
        'tables': {},           # 사주표 {이름: 데이터}
    }
    
    for name, data in images.items():
        name_lower = name.lower()
        
        if "표지" in name or "cover" in name_lower:
            result['cover'] = data
        elif "장배경" in name or "chapter" in name_lower:
            result['chapter_bg'] = data
        elif "내지" in name or "bg" in name_lower or "page" in name_lower:
            result['page_bg'] = data
        elif "목차" in name or "toc" in name_lower:
            result['toc'].append((name, data))
        elif "안내" in name or "guide" in name_lower:
            result['guide'].append((name, data))
        else:
            # 사주표 이미지
            result['tables'][name] = data
    
    # 정렬
    result['toc'].sort(key=lambda x: x[0])
    result['guide'].sort(key=lambda x: x[0])
    
    return result


def find_image_by_tag(text: str, images_dict: Dict[str, bytes]) -> Tuple[str, bytes, str]:
    """
    {{IMG:태그명}} 형식에서 이미지 찾기
    
    Returns:
        (태그명, 이미지데이터, 파일명) 또는 (태그명, None, None)
    """
    pattern = re.compile(r'\{\{IMG:([^}]+)\}\}')
    match = pattern.search(text)
    
    if not match:
        return (None, None, None)
    
    tag_name = match.group(1).strip()
    
    for img_name, img_data in images_dict.items():
        # 파일명에서 확장자 제거
        img_base = os.path.splitext(img_name)[0]
        
        # 매칭 조건
        if (tag_name == img_name or 
            tag_name == img_base or
            tag_name in img_name or
            img_base.endswith(tag_name)):
            return (tag_name, img_data, img_name)
    
    return (tag_name, None, None)


def create_pdf(
    docx_contents: List[Tuple[str, List[Dict]]],  # [(파일명, 내용), ...]
    images: Dict[str, bytes],  # {파일명: 바이트}
    customer_name: str,
    output_path: str = None,
    progress_callback: Callable[[float, str], None] = None,
    fonts_dir: str = None
) -> io.BytesIO:
    """
    PDF 생성 메인 함수
    
    Args:
        docx_contents: [(파일명, 내용리스트), ...] - 장별 Docx 내용
        images: {파일명: 바이트데이터} - 모든 이미지
        customer_name: 고객 이름
        output_path: 저장 경로 (없으면 BytesIO 반환)
        progress_callback: 진행상황 콜백 (progress, status_text)
        fonts_dir: 폰트 폴더 경로
        
    Returns:
        PDF BytesIO 버퍼
    """
    font_name, bold_name = setup_fonts(fonts_dir)
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 폰트 크기
    TITLE_SIZE = 30
    SUBTITLE_SIZE = 25
    BODY_SIZE = 17
    
    # 줄간격 (170%)
    LINE_HEIGHT = int(BODY_SIZE * 1.7)
    
    # 여백 설정 (mm → pt)
    MARGIN_TOP = 15 * 2.83465
    MARGIN_BOTTOM = 15 * 2.83465
    MARGIN_LEFT = 25 * 2.83465
    MARGIN_RIGHT = 25 * 2.83465
    
    MAX_WIDTH = width - MARGIN_LEFT - MARGIN_RIGHT
    
    # 이미지 분류
    classified = classify_images(images)
    cover_img = classified['cover']
    page_bg_img = classified['page_bg']
    chapter_bg_img = classified['chapter_bg']
    toc_images = classified['toc']
    guide_images = classified['guide']
    table_images = classified['tables']
    
    total_steps = len(docx_contents) + 3
    current_step = 0
    
    def update_progress(status: str):
        nonlocal current_step
        if progress_callback:
            progress_callback(current_step / total_steps, status)
    
    # ============================================
    # 1. 표지
    # ============================================
    update_progress("📄 표지 생성 중...")
    
    if cover_img:
        try:
            img_buffer = io.BytesIO(cover_img)
            c.drawImage(ImageReader(img_buffer), 0, 0, width=width, height=height)
        except:
            pass
    
    c.setFont(font_name, 28)
    name_text = f"{customer_name} 님"
    text_width = c.stringWidth(name_text, font_name, 28)
    c.drawString((width - text_width) / 2, height * 0.2, name_text)
    c.showPage()
    current_step += 1
    
    # ============================================
    # 2. 목차 (이미지)
    # ============================================
    update_progress("📋 목차 생성 중...")
    
    for toc_name, toc_data in toc_images:
        try:
            img_buffer = io.BytesIO(toc_data)
            pil_img = Image.open(img_buffer)
            img_w, img_h = pil_img.size
            
            scale = min(width / img_w, height / img_h, 1)
            new_w = img_w * scale
            new_h = img_h * scale
            
            img_buffer.seek(0)
            c.drawImage(
                ImageReader(img_buffer),
                (width - new_w) / 2,
                (height - new_h) / 2,
                width=new_w, height=new_h,
                mask='auto'
            )
        except:
            pass
        c.showPage()
    
    current_step += 1
    
    # ============================================
    # 3. 본문 (장별)
    # ============================================
    page_num = 2 + len(toc_images)
    IMG_TAG_PATTERN = re.compile(r'\{\{IMG:([^}]+)\}\}')
    
    def has_img_tag(text):
        return bool(IMG_TAG_PATTERN.search(text))
    
    def is_chapter_title(text):
        return text.startswith("제") and "장" in text[:10]
    
    def is_subtitle(text):
        # ▶, ●, ◆ 등으로 시작하거나 특정 패턴
        return any(text.startswith(c) for c in ['▶', '●', '◆', '★', '■', '□', '○'])
    
    used_images = set()
    
    for doc_idx, (doc_name, content) in enumerate(docx_contents):
        update_progress(f"📝 {doc_name} 처리 중...")
        
        # 새 페이지 함수
        def new_page():
            nonlocal page_num, y
            c.setFont(font_name, 10)
            c.drawString(width - MARGIN_RIGHT, MARGIN_BOTTOM, str(page_num))
            c.showPage()
            page_num += 1
            
            # 내지 배경
            if page_bg_img:
                try:
                    img_buffer = io.BytesIO(page_bg_img)
                    c.drawImage(ImageReader(img_buffer), 0, 0, width=width, height=height)
                except:
                    pass
            
            y = height - MARGIN_TOP - 40
        
        y = height - MARGIN_TOP
        first_item = True
        i = 0
        
        while i < len(content):
            text = content[i]["text"]
            style = content[i]["style"]
            
            # ★ 장 제목 ★
            if is_chapter_title(text) and first_item:
                # 장 배경
                if chapter_bg_img:
                    try:
                        img_buffer = io.BytesIO(chapter_bg_img)
                        c.drawImage(ImageReader(img_buffer), 0, 0, width=width, height=height)
                    except:
                        pass
                
                # 제목 추출 (예: "제1장 원국분석" → "제1장", "원국분석")
                parts = text.split(maxsplit=1)
                main_title = parts[0] if parts else text
                sub_title = parts[1] if len(parts) > 1 else ""
                
                # 메인 제목
                c.setFont(bold_name, TITLE_SIZE)
                title_width = c.stringWidth(main_title, bold_name, TITLE_SIZE)
                c.drawString((width - title_width) / 2, height * 0.55, main_title)
                
                # 부제목
                if sub_title:
                    c.setFont(font_name, SUBTITLE_SIZE)
                    sub_width = c.stringWidth(sub_title, font_name, SUBTITLE_SIZE)
                    c.drawString((width - sub_width) / 2, height * 0.55 - TITLE_SIZE - 15, sub_title)
                
                c.showPage()
                page_num += 1
                
                # 새 페이지 시작
                if page_bg_img:
                    try:
                        img_buffer = io.BytesIO(page_bg_img)
                        c.drawImage(ImageReader(img_buffer), 0, 0, width=width, height=height)
                    except:
                        pass
                
                y = height - MARGIN_TOP - 40
                first_item = False
                i += 1
                continue
            
            # ★ 이미지 태그 ★
            if has_img_tag(text):
                tag_name, img_data, img_name = find_image_by_tag(text, table_images)
                
                if img_data and img_name not in used_images:
                    try:
                        img_buffer = io.BytesIO(img_data)
                        pil_img = Image.open(img_buffer)
                        img_w, img_h = pil_img.size
                        
                        # 최대 너비/높이 제한
                        scale = min(MAX_WIDTH / img_w, (height * 0.5) / img_h, 1)
                        new_w = img_w * scale
                        new_h = img_h * scale
                        
                        # 페이지 넘김 체크
                        if y - new_h < MARGIN_BOTTOM + 40:
                            new_page()
                        
                        img_buffer.seek(0)
                        img_x = (width - new_w) / 2
                        img_y = y - new_h
                        
                        c.drawImage(
                            ImageReader(img_buffer),
                            img_x, img_y,
                            width=new_w, height=new_h,
                            mask='auto'
                        )
                        
                        used_images.add(img_name)
                        y = img_y - LINE_HEIGHT * 2
                        
                    except Exception:
                        pass
                
                i += 1
                continue
            
            # ★ 소제목 ★
            if is_subtitle(text):
                c.setFont(font_name, SUBTITLE_SIZE)
                
                # 줄바꿈 처리
                subtitle_lines = []
                line = ""
                for char in text:
                    if c.stringWidth(line + char, font_name, SUBTITLE_SIZE) < MAX_WIDTH:
                        line += char
                    else:
                        subtitle_lines.append(line)
                        line = char
                if line:
                    subtitle_lines.append(line)
                
                subtitle_height = len(subtitle_lines) * (SUBTITLE_SIZE + 5) + LINE_HEIGHT * 2
                
                if y - subtitle_height < MARGIN_BOTTOM + 40:
                    new_page()
                    c.setFont(font_name, SUBTITLE_SIZE)
                
                y -= LINE_HEIGHT * 2
                
                for ln in subtitle_lines:
                    c.drawString(MARGIN_LEFT, y, ln)
                    y -= SUBTITLE_SIZE + 5
                
                y -= 10
                i += 1
                continue
            
            # ★ 본문 ★
            c.setFont(font_name, BODY_SIZE)
            
            lines = []
            line = ""
            for char in text:
                if c.stringWidth(line + char, font_name, BODY_SIZE) < MAX_WIDTH:
                    line += char
                else:
                    lines.append(line)
                    line = char
            if line:
                lines.append(line)
            
            for ln in lines:
                if y < MARGIN_BOTTOM + 40:
                    new_page()
                    c.setFont(font_name, BODY_SIZE)
                
                c.drawString(MARGIN_LEFT, y, ln)
                y -= LINE_HEIGHT
            
            y -= 5
            first_item = False
            i += 1
        
        # 장 끝
        c.setFont(font_name, 10)
        c.drawString(width - MARGIN_RIGHT, MARGIN_BOTTOM, str(page_num))
        c.showPage()
        page_num += 1
        
        current_step += 1
    
    # ============================================
    # 4. 안내 페이지
    # ============================================
    update_progress("📄 안내 페이지 생성 중...")
    
    for guide_name, guide_data in guide_images:
        try:
            img_buffer = io.BytesIO(guide_data)
            pil_img = Image.open(img_buffer)
            img_w, img_h = pil_img.size
            
            scale = min(width / img_w, height / img_h, 1)
            new_w = img_w * scale
            new_h = img_h * scale
            
            img_buffer.seek(0)
            c.drawImage(
                ImageReader(img_buffer),
                (width - new_w) / 2,
                (height - new_h) / 2,
                width=new_w, height=new_h,
                mask='auto'
            )
        except:
            pass
        c.showPage()
    
    if progress_callback:
        progress_callback(1.0, "✅ PDF 생성 완료!")
    
    c.save()
    buffer.seek(0)
    
    # 파일로 저장
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
        buffer.seek(0)
    
    return buffer


def create_pdf_from_files(
    docx_paths: List[str],
    image_paths: List[str],
    customer_name: str,
    output_path: str,
    progress_callback: Callable[[float, str], None] = None,
    fonts_dir: str = None
) -> str:
    """
    파일 경로로부터 PDF 생성 (편의 함수)
    
    Args:
        docx_paths: Docx 파일 경로 리스트
        image_paths: 이미지 파일 경로 리스트
        customer_name: 고객 이름
        output_path: 저장 경로
        progress_callback: 진행 콜백
        fonts_dir: 폰트 폴더
        
    Returns:
        저장된 PDF 경로
    """
    # Docx 읽기
    docx_contents = []
    for path in sorted(docx_paths):
        name = os.path.basename(path)
        content = read_docx(path)
        if content:
            docx_contents.append((name, content))
    
    # 이미지 읽기
    images = {}
    for path in image_paths:
        name = os.path.basename(path)
        with open(path, 'rb') as f:
            images[name] = f.read()
    
    # PDF 생성
    create_pdf(
        docx_contents=docx_contents,
        images=images,
        customer_name=customer_name,
        output_path=output_path,
        progress_callback=progress_callback,
        fonts_dir=fonts_dir
    )
    
    return output_path


# ============================================
# 테스트
# ============================================
if __name__ == "__main__":
    print("PDF Generator 모듈 로드 완료")
    print(f"폰트 설정: {setup_fonts()}")
