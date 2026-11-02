# 정비사업 법령 모니터링

기존 info 사이트와 분리된 웹 애플리케이션입니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 설정

Streamlit Cloud Secrets 또는 서버 환경변수에 LAW_OC, OPENAI_API_KEY, APP_PASSWORD를 설정하세요. 비밀값은 GitHub에 올리지 마세요.

GitHub Pages는 정적 호스팅이므로 Python/SQLite/OpenAI API 서버를 실행할 수 없습니다. Streamlit Cloud 등 별도 Python 호스팅이 필요합니다.

## 데이터

SQLite는 서버 로컬 파일이므로 클라우드 재시작 시 유실될 수 있습니다. 운영용으로는 영구 데이터베이스 연동이 필요합니다.
