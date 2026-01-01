# -*- coding: utf-8 -*-
"""
☁️ Google Drive 업로드 모듈
- 서비스 계정 인증
- 파일 업로드
- 공유 링크 생성
"""

import os
import json
from typing import Optional, Dict


def upload_to_drive(
    file_path: str,
    folder_id: str,
    credentials_json: str,
    file_name: str = None,
    make_public: bool = True
) -> Dict:
    """
    Google Drive에 파일 업로드
    
    Args:
        file_path: 업로드할 파일 경로
        folder_id: 드라이브 폴더 ID
        credentials_json: 서비스 계정 JSON 문자열 또는 파일 경로
        file_name: 드라이브에 저장할 파일명 (없으면 원본 파일명)
        make_public: 공개 링크 생성 여부
        
    Returns:
        {'file_id': str, 'web_link': str, 'download_link': str}
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise ImportError("google-api-python-client, google-auth 설치 필요")
    
    # 인증
    if os.path.exists(credentials_json):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    else:
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # 파일명
    if file_name is None:
        file_name = os.path.basename(file_path)
    
    # 파일 메타데이터
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    # MIME 타입
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.zip': 'application/zip',
    }
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = mime_types.get(ext, 'application/octet-stream')
    
    # 업로드
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    file_id = file.get('id')
    web_link = file.get('webViewLink')
    
    # 공개 권한 설정
    if make_public:
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
    
    # 다운로드 링크
    download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    return {
        'file_id': file_id,
        'web_link': web_link,
        'download_link': download_link
    }


def create_folder(
    folder_name: str,
    parent_folder_id: str,
    credentials_json: str
) -> str:
    """
    드라이브에 폴더 생성
    
    Returns:
        생성된 폴더 ID
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("google-api-python-client, google-auth 설치 필요")
    
    # 인증
    if os.path.exists(credentials_json):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    else:
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    
    service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')


def list_files_in_folder(
    folder_id: str,
    credentials_json: str
) -> list:
    """
    폴더 내 파일 목록 조회
    
    Returns:
        [{'id': str, 'name': str, 'mimeType': str}, ...]
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("google-api-python-client, google-auth 설치 필요")
    
    if os.path.exists(credentials_json):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    else:
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    
    service = build('drive', 'v3', credentials=credentials)
    
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType)"
    ).execute()
    
    return results.get('files', [])


# ============================================
# 테스트
# ============================================
if __name__ == "__main__":
    print("Google Drive 모듈 로드 완료")
    print("필요 라이브러리: pip install google-api-python-client google-auth")
