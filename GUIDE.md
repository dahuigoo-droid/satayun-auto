# 🚀 사주 보고서 완전 자동화 시스템 - 실행 가이드

## 📋 시스템 구성

| 구성 | 기능 |
|-----|------|
| A 로컬 실행 | 끊김 없음 |
| B 병렬 처리 | 10분/1명 |
| C 배치 스크립트 | 엑셀 자동 처리 |
| PDF 출력 | 150페이지 완성본 |
| 자동 발송 | 이메일/드라이브 |

---

## 1️⃣ 설치 (최초 1회)

```bash
# 1. 프로젝트 폴더로 이동
cd satayun-auto-v2

# 2. 필수 패키지 설치
pip install anthropic pandas openpyxl pillow reportlab python-docx korean-lunar-calendar google-api-python-client google-auth requests

# 3. 설정 파일 생성
cp config.sample.json config.json
```

---

## 2️⃣ 설정 (config.json)

```json
{
    "anthropic_api_key": "sk-ant-xxx...",  ← 필수!
    "model": "claude-sonnet-4-20250514",
    
    "gmail_email": "your@gmail.com",       ← 이메일 발송용
    "gmail_password": "앱비밀번호",
    
    "drive_folder_id": "폴더ID",           ← 드라이브 업로드용
    "drive_credentials": "JSON내용",
    
    "output_dir": "./output",
    "parallel_chapters": 5                  ← 동시 생성 장 수
}
```

### API 키만 있으면 최소 실행 가능!

```json
{
    "anthropic_api_key": "sk-ant-xxx..."
}
```

---

## 3️⃣ 엑셀 준비

`고객목록.xlsx` 형식:

| 이름 | 생년월일 | 시 | 분 | 성별 | 음양력 | 윤달 | 이메일 | 전화번호 |
|-----|---------|----|----|-----|-------|-----|--------|---------|
| 홍길동 | 1990-05-15 | 14 | 30 | 남성 | 양력 | FALSE | hong@email.com | 01012345678 |
| 김철수 | 1985-12-03 | 6 | 0 | 남성 | 음력 | FALSE | kim@email.com | 01098765432 |

---

## 4️⃣ 실행 방법

### A. 배치 처리 (30명 자동)

```bash
python batch_processor.py 고객목록.xlsx
```

결과:
```
[1/30] 홍길동 처리 시작...
  → 홍길동: 사주 계산 중...
  → 홍길동: 이미지 17종 생성 중...
  → 홍길동: Claude API 15장 생성 중 (병렬)...
  → 홍길동: PDF 조립 중...
  → 홍길동: Drive 업로드 중...
  → 홍길동: 이메일 발송 중...
  ✅ 홍길동 완료!
     Drive: https://drive.google.com/...
     이메일: 발송 완료

[2/30] 김철수 처리 시작...
...
```

### B. 단일 테스트

```bash
python batch_processor.py --test 홍길동 1990-05-15 14 30 남성 양력
```

---

## 5️⃣ 출력 결과

```
output/
├── 홍길동/
│   ├── images/
│   │   ├── 01_원국표.png
│   │   ├── 02_대운표.png
│   │   └── ...
│   └── 홍길동_사주보고서.pdf  ← 150페이지 PDF
├── 김철수/
│   └── ...
└── 결과_20250101_120000.xlsx  ← 발송 결과 리포트
```

---

## 6️⃣ 예상 시간/비용

### 시간
| 고객 수 | 소요 시간 |
|--------|----------|
| 1명 | ~10분 |
| 10명 | ~1.5시간 |
| 30명 | ~5시간 |

### 비용 (Claude Sonnet 4 기준)
| 고객 수 | API 비용 |
|--------|---------|
| 1명 | ~$0.50 (약 700원) |
| 10명 | ~$5 (약 7,000원) |
| 30명 | ~$15 (약 21,000원) |

---

## 7️⃣ 자주 묻는 질문

### Q. 중간에 오류나면?
A. `output/` 폴더에 이미 완료된 고객은 저장됨. 
   실패한 고객만 엑셀에서 다시 실행하면 됨.

### Q. 병렬 수 조절?
A. `config.json`에서 `parallel_chapters` 값 변경
   - 5: 기본 (안정)
   - 10: 빠름 (API 제한 주의)

### Q. 카카오 알림톡은?
A. 별도 비즈메시지 계약 필요. 
   현재는 로그만 남기고 수동 발송 권장.

---

## 8️⃣ 문제 해결

### "API key not found"
→ `config.json`에 `anthropic_api_key` 확인

### "마스터 프롬프트 없음"
→ `prompts/00_master_prompt.txt` 파일 확인

### "이미지 생성 오류"
→ `fonts/ChosunGs.TTF` 폰트 파일 확인

---

## 🎯 추천 워크플로우

```
1. 오전: 엑셀 준비 (30명)
2. 점심: 배치 실행 시작
3. 퇴근: 자동 처리 중
4. 다음날 아침: 완료 확인 + 발송 결과 체크
```

---

**문의사항은 Claude에게 물어보세요!**
