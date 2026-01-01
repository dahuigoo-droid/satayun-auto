# 🔮 사주 통합 자동화 시스템 v2

생년월일시 입력 → 이미지 생성 → AI 해석 → PDF 조립 → 이메일 발송

## ✨ 주요 기능

| 기능 | 설명 |
|-----|------|
| 📊 이미지 생성 | 사주표 17종 자동 생성 |
| 🤖 Claude API | 장별 해석 자동 생성 |
| 📄 PDF 조립 | Docx + 이미지 → PDF |
| ☁️ Drive 업로드 | Google Drive 자동 업로드 |
| 📧 이메일 발송 | Gmail SMTP 자동 발송 |

## 📁 파일 구조

```
satayun-auto-v2/
├── app.py                  # 통합 메인 앱
├── saju_calculator.py      # 사주 계산
├── image_generator.py      # 이미지 생성
├── pdf_generator.py        # PDF 조립
├── claude_api.py           # Claude API
├── delivery.py             # 이메일/카카오 발송
├── google_drive.py         # 드라이브 업로드
├── prompts/                # 장별 프롬프트
│   ├── 01_원국분석.txt
│   ├── 02_대운분석.txt
│   └── ...
├── fonts/                  # 폰트
│   └── ChosunGs.TTF
└── requirements.txt
```

## 🚀 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

## 📊 탭 구성

| 탭 | 기능 |
|----|------|
| 📝 개별 입력 | 1명씩 이미지 생성 |
| 📊 엑셀 일괄 | 여러 명 일괄 처리 |
| 📅 일진표 | 12개월 일진표 |
| 📄 보고서 생성 | Claude API + PDF |
| 📧 발송 관리 | 이메일/드라이브 |

## ⚙️ 필요한 설정

### 1. Anthropic API Key
- https://console.anthropic.com

### 2. Gmail 앱 비밀번호
1. Google 계정 → 보안 → 2단계 인증 활성화
2. 앱 비밀번호 생성 (16자리)

### 3. Google Drive (선택)
1. GCP 서비스 계정 생성
2. JSON 키 다운로드
3. 드라이브 폴더에 서비스 계정 공유

## 💰 예상 비용 (Claude API)

| 모델 | 6장 기준 | 1명당 |
|------|---------|-------|
| Sonnet 4 | ~30,000 토큰 | ~$0.10 (약 140원) |
| Haiku 3.5 | ~30,000 토큰 | ~$0.02 (약 30원) |

---

v2.0 - 통합 자동화 시스템
