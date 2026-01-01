# -*- coding: utf-8 -*-
"""
📧 이메일 & 💬 카카오 발송 모듈
- Gmail SMTP 이메일 발송
- 카카오 알림톡/친구톡 발송
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict
import requests


# ============================================
# 이메일 발송 (Gmail SMTP)
# ============================================
def send_email(
    to_email: str,
    subject: str,
    body: str,
    sender_email: str,
    sender_password: str,
    attachments: List[str] = None,
    drive_link: str = None,
    html: bool = True
) -> Dict:
    """
    이메일 발송
    
    Args:
        to_email: 수신자 이메일
        subject: 제목
        body: 본문 (HTML 또는 텍스트)
        sender_email: 발신자 Gmail
        sender_password: 앱 비밀번호 (16자리)
        attachments: 첨부 파일 경로 리스트
        drive_link: 드라이브 링크 (본문에 자동 추가)
        html: HTML 형식 여부
        
    Returns:
        {'success': bool, 'message': str}
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # 드라이브 링크 추가
        if drive_link:
            if html:
                body += f"""
                <br><br>
                <hr>
                <p><strong>📥 파일 다운로드</strong></p>
                <p><a href="{drive_link}" target="_blank">여기를 클릭하여 파일을 다운로드하세요</a></p>
                """
            else:
                body += f"\n\n---\n📥 파일 다운로드: {drive_link}"
        
        # 본문
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        # 첨부 파일
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read())
                        part.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=os.path.basename(file_path)
                        )
                        msg.attach(part)
        
        # SMTP 연결 및 전송
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        return {'success': True, 'message': f'이메일 발송 완료: {to_email}'}
    
    except Exception as e:
        return {'success': False, 'message': f'발송 실패: {str(e)}'}


def send_bulk_emails(
    recipients: List[Dict],  # [{'email': str, 'name': str, 'drive_link': str}, ...]
    subject_template: str,
    body_template: str,
    sender_email: str,
    sender_password: str
) -> List[Dict]:
    """
    대량 이메일 발송
    
    Args:
        recipients: 수신자 목록
        subject_template: 제목 템플릿 ({name} 치환 가능)
        body_template: 본문 템플릿 ({name}, {drive_link} 치환 가능)
        
    Returns:
        [{'email': str, 'success': bool, 'message': str}, ...]
    """
    results = []
    
    for recipient in recipients:
        email = recipient.get('email')
        name = recipient.get('name', '고객')
        drive_link = recipient.get('drive_link', '')
        
        subject = subject_template.format(name=name)
        body = body_template.format(name=name, drive_link=drive_link)
        
        result = send_email(
            to_email=email,
            subject=subject,
            body=body,
            sender_email=sender_email,
            sender_password=sender_password,
            drive_link=drive_link
        )
        
        results.append({
            'email': email,
            'success': result['success'],
            'message': result['message']
        })
    
    return results


# ============================================
# 카카오 알림톡 발송 (비즈메시지)
# ============================================
def send_kakao_alimtalk(
    to_phone: str,
    template_code: str,
    template_data: Dict,
    kakao_api_key: str,
    sender_key: str,
    profile_key: str = None
) -> Dict:
    """
    카카오 알림톡 발송 (비즈메시지 API)
    
    ※ 사전에 카카오 비즈니스 채널 등록 및 템플릿 승인 필요
    
    Args:
        to_phone: 수신자 전화번호 (01012345678)
        template_code: 승인된 템플릿 코드
        template_data: 템플릿 변수 딕셔너리
        kakao_api_key: API 키
        sender_key: 발신 프로필 키
        profile_key: 프로필 키 (선택)
        
    Returns:
        {'success': bool, 'message': str, 'response': dict}
    """
    # ※ 실제 구현은 사용하는 알림톡 서비스에 따라 다름
    # 예: NHN Cloud, 인포뱅크, 다우기술 등
    
    # 예시: NHN Cloud 알림톡 API
    url = "https://api-alimtalk.cloud.toast.com/alimtalk/v2.2/appkeys/{}/messages".format(kakao_api_key)
    
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Secret-Key": kakao_api_key
    }
    
    data = {
        "senderKey": sender_key,
        "templateCode": template_code,
        "recipientList": [{
            "recipientNo": to_phone,
            "templateParameter": template_data
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': f'알림톡 발송 완료: {to_phone}',
                'response': result
            }
        else:
            return {
                'success': False,
                'message': f'발송 실패: {result}',
                'response': result
            }
    except Exception as e:
        return {
            'success': False,
            'message': f'발송 오류: {str(e)}',
            'response': None
        }


def send_kakao_friendtalk(
    to_phone: str,
    message: str,
    kakao_api_key: str,
    sender_key: str,
    button_link: str = None,
    button_text: str = "파일 다운로드"
) -> Dict:
    """
    카카오 친구톡 발송 (친구 추가된 사용자에게만)
    
    Args:
        to_phone: 수신자 전화번호
        message: 메시지 내용
        kakao_api_key: API 키
        sender_key: 발신 프로필 키
        button_link: 버튼 링크 URL
        button_text: 버튼 텍스트
        
    Returns:
        {'success': bool, 'message': str}
    """
    # ※ 실제 구현은 사용하는 서비스에 따라 다름
    
    url = "https://api-alimtalk.cloud.toast.com/friendtalk/v2.2/appkeys/{}/messages".format(kakao_api_key)
    
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Secret-Key": kakao_api_key
    }
    
    recipient = {
        "recipientNo": to_phone,
        "content": message
    }
    
    # 버튼 추가
    if button_link:
        recipient["buttons"] = [{
            "ordering": 1,
            "type": "WL",
            "name": button_text,
            "linkMo": button_link,
            "linkPc": button_link
        }]
    
    data = {
        "senderKey": sender_key,
        "recipientList": [recipient]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            return {'success': True, 'message': f'친구톡 발송 완료: {to_phone}'}
        else:
            return {'success': False, 'message': f'발송 실패: {result}'}
    except Exception as e:
        return {'success': False, 'message': f'발송 오류: {str(e)}'}


# ============================================
# 이메일 템플릿
# ============================================
DEFAULT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: '맑은 고딕', sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4A90A4; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background: #f9f9f9; }}
        .button {{ 
            display: inline-block; 
            background: #4A90A4; 
            color: white; 
            padding: 15px 30px; 
            text-decoration: none; 
            border-radius: 5px;
            margin-top: 20px;
        }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 사주 분석 보고서</h1>
        </div>
        <div class="content">
            <p><strong>{name}</strong>님, 안녕하세요!</p>
            <p>요청하신 사주 분석 보고서가 준비되었습니다.</p>
            <p>아래 버튼을 클릭하여 다운로드해주세요.</p>
            <p style="text-align: center;">
                <a href="{drive_link}" class="button">📥 보고서 다운로드</a>
            </p>
            <p style="margin-top: 30px; color: #666;">
                ※ 다운로드가 안 될 경우, 아래 링크를 브라우저에 직접 붙여넣기 해주세요.<br>
                <small>{drive_link}</small>
            </p>
        </div>
        <div class="footer">
            <p>본 메일은 발신전용입니다.</p>
            <p>문의사항은 카카오톡으로 연락주세요.</p>
        </div>
    </div>
</body>
</html>
"""


def get_default_email_template() -> str:
    """기본 이메일 템플릿 반환"""
    return DEFAULT_EMAIL_TEMPLATE


# ============================================
# 테스트
# ============================================
if __name__ == "__main__":
    print("발송 모듈 로드 완료")
    print("\n[Gmail 설정 방법]")
    print("1. Google 계정 → 보안 → 2단계 인증 활성화")
    print("2. 앱 비밀번호 생성 (16자리)")
    print("3. sender_password에 앱 비밀번호 입력")
