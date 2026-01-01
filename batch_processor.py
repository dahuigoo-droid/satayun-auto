# -*- coding: utf-8 -*-
"""
🚀 사주 보고서 완전 자동화 시스템
- 엑셀 30명 일괄 처리
- 병렬 처리 (15장 동시 생성)
- PDF 150페이지 자동 조립
- Google Drive 업로드
- 이메일/카카오 자동 발송
"""

import os
import sys
import json
import time
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 로컬 모듈
from saju_calculator import (
    calc_사주, calc_대운, calc_세운, calc_월운, calc_신살,
    음력_to_양력, 양력_to_음력, 음력_문자열
)
from image_generator import (
    create_원국표, create_대운표, create_세운표, create_월운표,
    create_오행차트, create_십성표, create_신살표, create_12운성표,
    create_지장간표, create_합충형파해표, create_궁성표, create_육친표,
    create_납음오행표, create_격국표, create_공망표, create_용신표,
    generate_gpt_text, ZODIAC_PATH
)
from pdf_generator_v2 import create_full_pdf
from google_drive import upload_to_drive
from delivery import send_email, get_default_email_template

# ============================================
# 설정
# ============================================
class Config:
    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @property
    def anthropic_api_key(self):
        return self.config.get('anthropic_api_key', os.environ.get('ANTHROPIC_API_KEY', ''))
    
    @property
    def model(self):
        return self.config.get('model', 'claude-sonnet-4-20250514')
    
    @property
    def gmail_email(self):
        return self.config.get('gmail_email', '')
    
    @property
    def gmail_password(self):
        return self.config.get('gmail_password', '')
    
    @property
    def drive_folder_id(self):
        return self.config.get('drive_folder_id', '')
    
    @property
    def drive_credentials(self):
        return self.config.get('drive_credentials', '')
    
    @property
    def kakao_api_key(self):
        return self.config.get('kakao_api_key', '')
    
    @property
    def kakao_sender_key(self):
        return self.config.get('kakao_sender_key', '')
    
    @property
    def output_dir(self):
        return self.config.get('output_dir', './output')
    
    @property
    def parallel_chapters(self):
        return self.config.get('parallel_chapters', 5)


# ============================================
# 장 목차
# ============================================
CHAPTER_INFO = {
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


# ============================================
# Claude API 병렬 호출
# ============================================
def generate_chapter(client, model, master_prompt, gpt_text, chapter_num, customer_name):
    """단일 장 생성"""
    chapter_title = CHAPTER_INFO.get(chapter_num, "")
    
    user_message = f"""[사주 데이터]
{gpt_text}

위 데이터를 바탕으로 "제{chapter_num}장. {chapter_title}"을 작성해주세요.
목차의 소주제를 모두 포함하여 작성하세요.
고객명: {customer_name}"""
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            system=master_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return chapter_num, response.content[0].text
    except Exception as e:
        return chapter_num, f"[오류] 제{chapter_num}장 생성 실패: {str(e)}"


def generate_all_chapters_parallel(api_key, model, master_prompt, gpt_text, customer_name, max_workers=5, progress_callback=None):
    """15장 병렬 생성"""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    
    chapters = {}
    total = 15
    completed = 0
    lock = threading.Lock()
    
    def update_progress(ch_num):
        nonlocal completed
        with lock:
            completed += 1
            if progress_callback:
                progress_callback(completed, total, f"제{ch_num}장 완료")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                generate_chapter, client, model, master_prompt, gpt_text, ch_num, customer_name
            ): ch_num for ch_num in range(1, 16)
        }
        
        for future in as_completed(futures):
            ch_num, content = future.result()
            chapters[ch_num] = content
            update_progress(ch_num)
    
    # 정렬해서 반환
    return {k: chapters[k] for k in sorted(chapters.keys())}


# ============================================
# 1명 고객 처리
# ============================================
def process_customer(row, config, master_prompt, progress_callback=None):
    """
    1명 고객 전체 처리
    
    Args:
        row: 엑셀 행 (이름, 생년월일, 시, 분, 성별, 음양력, 윤달, 이메일, 전화번호)
        config: Config 객체
        master_prompt: 마스터 프롬프트
        progress_callback: (step, total_steps, message) 콜백
    
    Returns:
        결과 딕셔너리
    """
    result = {
        'name': row['이름'],
        'success': False,
        'pdf_path': None,
        'drive_link': None,
        'email_sent': False,
        'kakao_sent': False,
        'error': None
    }
    
    try:
        name = row['이름']
        
        # ============================================
        # 1단계: 사주 계산
        # ============================================
        if progress_callback:
            progress_callback(1, 7, f"{name}: 사주 계산 중...")
        
        # 날짜 파싱
        birth_date = row['생년월일']
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d')
        
        input_year = birth_date.year
        input_month = birth_date.month
        input_day = birth_date.day
        hour = int(row.get('시', 12))
        minute = int(row.get('분', 0))
        gender_str = row.get('성별', '남성')
        calendar_type = row.get('음양력', '양력')
        is_leap = row.get('윤달', False)
        
        if calendar_type == "음력":
            year, month, day = 음력_to_양력(input_year, input_month, input_day, is_leap)
            음력_str = 음력_문자열(input_year, input_month, input_day, is_leap)
            양력_str = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"
        else:
            year, month, day = input_year, input_month, input_day
            양력_str = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"
            음력_year, 음력_month, 음력_day, 음력_윤달 = 양력_to_음력(year, month, day)
            음력_str = 음력_문자열(음력_year, 음력_month, 음력_day, 음력_윤달)
        
        사주 = calc_사주(year, month, day, hour, minute)
        나이 = datetime.now().year - year + 1
        gender = '남' if gender_str == '남성' else '여'
        
        기본정보 = {
            '이름': name,
            '성별': gender_str,
            '나이': 나이,
            '양력': 양력_str,
            '음력': 음력_str,
        }
        
        # 운세 계산
        대운_data = calc_대운(year, month, day, hour, minute, gender)
        세운_data = calc_세운(year, month, day, hour, minute)
        월운_data = calc_월운(year, month, day, hour, minute)
        신살_data = calc_신살(사주, gender)
        
        # GPT 텍스트
        gpt_text = generate_gpt_text(사주, 기본정보, gender, 대운_data, 세운_data, 월운_data, 신살_data)
        
        # ============================================
        # 2단계: 이미지 17종 생성
        # ============================================
        if progress_callback:
            progress_callback(2, 7, f"{name}: 이미지 17종 생성 중...")
        
        img_dir = os.path.join(config.output_dir, name, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        # 이미지 생성
        create_원국표(사주, 기본정보, f"{img_dir}/01_원국표.png", 신살_data, ZODIAC_PATH)
        create_대운표(대운_data, 기본정보, f"{img_dir}/02_대운표.png")
        create_세운표(세운_data, 기본정보, f"{img_dir}/03_세운표.png")
        create_월운표(월운_data, 기본정보, f"{img_dir}/04_월운표.png")
        create_오행차트(사주, 기본정보, f"{img_dir}/05_오행분석.png")
        create_십성표(사주, 기본정보, f"{img_dir}/06_십성표.png")
        create_신살표(신살_data, 기본정보, f"{img_dir}/07_신살표.png")
        create_12운성표(사주, 기본정보, f"{img_dir}/08_12운성표.png")
        create_지장간표(사주, 기본정보, f"{img_dir}/09_지장간표.png")
        create_합충형파해표(사주, 기본정보, f"{img_dir}/10_합충형파해표.png")
        create_궁성표(사주, 기본정보, f"{img_dir}/11_궁성표.png")
        create_육친표(사주, 기본정보, gender, f"{img_dir}/12_육친표.png")
        create_납음오행표(사주, 기본정보, f"{img_dir}/13_납음오행표.png")
        create_격국표(사주, 기본정보, f"{img_dir}/14_격국표.png")
        create_공망표(사주, 기본정보, f"{img_dir}/15_공망표.png")
        create_용신표(사주, 기본정보, f"{img_dir}/16_용신표.png")
        
        # ============================================
        # 3단계: Claude API 15장 병렬 생성
        # ============================================
        if progress_callback:
            progress_callback(3, 7, f"{name}: Claude API 15장 생성 중 (병렬)...")
        
        def chapter_progress(completed, total, msg):
            if progress_callback:
                progress_callback(3, 7, f"{name}: {msg} ({completed}/{total})")
        
        chapters = generate_all_chapters_parallel(
            api_key=config.anthropic_api_key,
            model=config.model,
            master_prompt=master_prompt,
            gpt_text=gpt_text,
            customer_name=name,
            max_workers=config.parallel_chapters,
            progress_callback=chapter_progress
        )
        
        # ============================================
        # 4단계: PDF 조립
        # ============================================
        if progress_callback:
            progress_callback(4, 7, f"{name}: PDF 조립 중...")
        
        pdf_dir = os.path.join(config.output_dir, name)
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"{name}_사주보고서.pdf")
        
        create_full_pdf(
            chapters=chapters,
            images_dir=img_dir,
            customer_name=name,
            output_path=pdf_path,
            기본정보=기본정보
        )
        
        result['pdf_path'] = pdf_path
        
        # ============================================
        # 5단계: Google Drive 업로드
        # ============================================
        if config.drive_folder_id and config.drive_credentials:
            if progress_callback:
                progress_callback(5, 7, f"{name}: Drive 업로드 중...")
            
            try:
                drive_result = upload_to_drive(
                    file_path=pdf_path,
                    folder_id=config.drive_folder_id,
                    credentials_json=config.drive_credentials,
                    file_name=f"{name}_사주보고서.pdf"
                )
                result['drive_link'] = drive_result['web_link']
            except Exception as e:
                print(f"[경고] {name} Drive 업로드 실패: {e}")
        
        # ============================================
        # 6단계: 이메일 발송
        # ============================================
        email = row.get('이메일', '')
        if email and config.gmail_email and config.gmail_password:
            if progress_callback:
                progress_callback(6, 7, f"{name}: 이메일 발송 중...")
            
            try:
                email_body = get_default_email_template().format(
                    name=name,
                    drive_link=result.get('drive_link', '')
                )
                
                email_result = send_email(
                    to_email=email,
                    subject=f"{name}님의 사주 분석 보고서",
                    body=email_body,
                    sender_email=config.gmail_email,
                    sender_password=config.gmail_password,
                    drive_link=result.get('drive_link')
                )
                
                result['email_sent'] = email_result['success']
            except Exception as e:
                print(f"[경고] {name} 이메일 발송 실패: {e}")
        
        # ============================================
        # 7단계: 카카오 알림톡 (선택)
        # ============================================
        phone = row.get('전화번호', '')
        if phone and config.kakao_api_key:
            if progress_callback:
                progress_callback(7, 7, f"{name}: 카카오 발송 중...")
            
            # 카카오 알림톡은 별도 설정 필요
            # 여기서는 로그만 남김
            print(f"[INFO] {name} 카카오 알림톡 발송 대기: {phone}")
        
        result['success'] = True
        
        if progress_callback:
            progress_callback(7, 7, f"{name}: ✅ 완료!")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"[오류] {row.get('이름', 'Unknown')} 처리 실패: {e}")
        import traceback
        traceback.print_exc()
    
    return result


# ============================================
# 메인 배치 처리
# ============================================
def process_batch(excel_path, config_path="config.json"):
    """
    엑셀 파일 일괄 처리
    
    Args:
        excel_path: 엑셀 파일 경로
        config_path: 설정 파일 경로
    """
    print("=" * 60)
    print("🚀 사주 보고서 완전 자동화 시스템")
    print("=" * 60)
    
    # 설정 로드
    config = Config(config_path)
    
    # API 키 확인
    if not config.anthropic_api_key:
        print("[오류] Anthropic API 키가 없습니다. config.json을 확인하세요.")
        return
    
    # 마스터 프롬프트 로드
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "00_master_prompt.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "00_마스터프롬프트.txt")
    
    if not os.path.exists(prompt_path):
        print(f"[오류] 마스터 프롬프트 파일이 없습니다: {prompt_path}")
        return
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        master_prompt = f.read()
    
    print(f"✅ 마스터 프롬프트 로드 완료")
    
    # 엑셀 로드
    df = pd.read_excel(excel_path)
    total_customers = len(df)
    print(f"✅ 엑셀 로드 완료: {total_customers}명")
    
    # 출력 폴더 생성
    os.makedirs(config.output_dir, exist_ok=True)
    
    # 결과 저장
    results = []
    start_time = time.time()
    
    # 고객별 처리
    for idx, row in df.iterrows():
        customer_num = idx + 1
        name = row.get('이름', f'고객{customer_num}')
        
        print(f"\n[{customer_num}/{total_customers}] {name} 처리 시작...")
        
        def progress_callback(step, total, msg):
            print(f"  → {msg}")
        
        result = process_customer(row, config, master_prompt, progress_callback)
        results.append(result)
        
        if result['success']:
            print(f"  ✅ {name} 완료!")
            if result['drive_link']:
                print(f"     Drive: {result['drive_link']}")
            if result['email_sent']:
                print(f"     이메일: 발송 완료")
        else:
            print(f"  ❌ {name} 실패: {result['error']}")
    
    # 결과 요약
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    
    print("\n" + "=" * 60)
    print("📊 처리 결과")
    print("=" * 60)
    print(f"전체: {total_customers}명")
    print(f"성공: {success_count}명")
    print(f"실패: {total_customers - success_count}명")
    print(f"소요시간: {elapsed/60:.1f}분")
    print(f"평균: {elapsed/total_customers/60:.1f}분/명")
    
    # 결과 저장
    result_df = pd.DataFrame(results)
    result_path = os.path.join(config.output_dir, f"결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    result_df.to_excel(result_path, index=False)
    print(f"\n📁 결과 파일: {result_path}")
    
    return results


# ============================================
# 단일 고객 테스트
# ============================================
def process_single(name, birth_date, hour, minute, gender, calendar_type, is_leap=False, email=None, config_path="config.json"):
    """
    단일 고객 처리 (테스트용)
    """
    row = {
        '이름': name,
        '생년월일': birth_date,
        '시': hour,
        '분': minute,
        '성별': gender,
        '음양력': calendar_type,
        '윤달': is_leap,
        '이메일': email or ''
    }
    
    config = Config(config_path)
    
    # 마스터 프롬프트 로드
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "00_master_prompt.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "00_마스터프롬프트.txt")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        master_prompt = f.read()
    
    def progress_callback(step, total, msg):
        print(f"[{step}/{total}] {msg}")
    
    result = process_customer(row, config, master_prompt, progress_callback)
    
    return result


# ============================================
# 실행
# ============================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  배치 처리: python batch_processor.py 고객목록.xlsx")
        print("  단일 테스트: python batch_processor.py --test 홍길동 1990-01-15 12 30 남성 양력")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        # 단일 테스트
        if len(sys.argv) < 8:
            print("사용법: python batch_processor.py --test 이름 생년월일 시 분 성별 음양력")
            sys.exit(1)
        
        result = process_single(
            name=sys.argv[2],
            birth_date=sys.argv[3],
            hour=int(sys.argv[4]),
            minute=int(sys.argv[5]),
            gender=sys.argv[6],
            calendar_type=sys.argv[7]
        )
        
        print("\n결과:", result)
    else:
        # 배치 처리
        process_batch(sys.argv[1])
