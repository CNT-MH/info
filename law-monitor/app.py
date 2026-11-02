import os, io, sqlite3, hashlib, hmac, datetime as dt
import requests
import streamlit as st
from openpyxl import Workbook

st.set_page_config(page_title="정비사업 법령 모니터링",layout="wide")
def setting(name):
    return os.getenv(name) or st.secrets.get(name,"")
password=setting("APP_PASSWORD")
if not password:
    st.error("APP_PASSWORD 환경변수를 먼저 설정하세요. 공개 접근을 차단했습니다.")
    st.stop()
entered=st.text_input("접근 비밀번호",type="password")
if not hmac.compare_digest(entered,password):
    st.stop()
db=sqlite3.connect("law_monitor.sqlite3")
db.execute("""CREATE TABLE IF NOT EXISTS laws(id INTEGER PRIMARY KEY, title TEXT, source_id TEXT, url TEXT, summary TEXT, message TEXT, status TEXT, content_hash TEXT UNIQUE, created_at TEXT)""")
db.commit()
st.title("정비사업 법령 모니터링")
st.caption("공식 원문 검수 후 카카오톡 전달 · 데이터는 서버 로컬 SQLite에 임시 저장")
tab1,tab2,tab3=st.tabs(["법령 검색","AI 요약·전달문","관리대장"])
with tab1:
    keyword=st.text_input("검색어","도시 및 주거환경정비법")
    if st.button("국가법령정보센터 검색"):
        oc=setting("LAW_OC")
        if not oc: st.error("LAW_OC 설정 필요")
        else:
            try:
                response=requests.get("https://www.law.go.kr/DRF/lawSearch.do",params={"OC":oc,"target":"law","type":"JSON","query":keyword,"display":20},timeout=20)
                response.raise_for_status()
                data=response.json()
                st.session_state["api_data"]=data
                st.success("응답 수신. 결과 구조를 확인하세요.")
            except Exception as e: st.error(f"API 호출 실패: {type(e).__name__}: {e}")
    if "api_data" in st.session_state:
        data=st.session_state["api_data"]
        rows=data.get("LawSearch",{}).get("law",[]) if isinstance(data,dict) else []
        if isinstance(rows,dict): rows=[rows]
        st.write(f"검색 결과: {len(rows)}건")
        for item in rows:
            title=item.get("법령명한글","")
            source_id=str(item.get("법령ID",""))
            if st.button(f"등록: {title} ({source_id})",key="law"+source_id):
                url="https://www.law.go.kr/법령/"+title
                digest=hashlib.sha256(("law:"+source_id).encode()).hexdigest()
                cur=db.execute("INSERT OR IGNORE INTO laws(title,source_id,url,summary,message,status,content_hash,created_at) VALUES(?,?,?,?,?,?,?,?)",(title,source_id,url,"","","검토 대기",digest,dt.datetime.now().isoformat()))
                db.commit()
                st.info("신규 등록" if cur.rowcount else "기존 정리 완료 / 신규 추가 불필요")
with tab2:
    rows=db.execute("SELECT id,title,url,summary,message FROM laws ORDER BY id DESC").fetchall()
    if rows:
        ids={f"{r[0]} | {r[1]}":r for r in rows}
        chosen=ids[st.selectbox("법령 선택",list(ids))]
        law_id,title,url,old_summary,old_message=chosen
        source=st.text_area("공식 원문 또는 검증할 개정내용 입력",height=180)
        if st.button("OpenAI 요약 생성"):
            key=setting("OPENAI_API_KEY")
            if not key: st.error("OPENAI_API_KEY 설정 필요")
            elif not source.strip(): st.warning("원문을 입력하세요.")
            else:
                try:
                    from openai import OpenAI
                    result=OpenAI(api_key=key).responses.create(model="gpt-4.1-mini",instructions="법령 원문에 근거하여 300자 내외 한국어로 요약하라. 불확실한 사실을 만들지 말고 발의/공포/시행을 혼동하지 말라. 카카오톡 전달용 문장만 작성하라.",input=source)
                    summary=result.output_text
                    message=f"{title}\n\n{summary}\n\n관련링크\n{url}"
                    db.execute("UPDATE laws SET summary=?,message=? WHERE id=?",(summary,message,law_id));db.commit()
                    st.success("초안 생성. 원문 대조 검수 필요")
                except Exception as e:st.error(f"요약 실패: {type(e).__name__}: {e}")
        message=db.execute("SELECT message FROM laws WHERE id=?",(law_id,)).fetchone()[0]
        edited=st.text_area("카카오톡 전달문 (수정·복사)",value=message,height=200)
        if st.button("전달문 수정 저장"):
            db.execute("UPDATE laws SET message=? WHERE id=?",(edited,law_id));db.commit()
        st.code(edited,language=None)
        if st.button("전달완료 처리"):
            db.execute("UPDATE laws SET status='전달 완료' WHERE id=?",(law_id,));db.commit();st.success("상태 저장")
with tab3:
    rows=db.execute("SELECT id,title,source_id,url,summary,message,status,created_at FROM laws ORDER BY id DESC").fetchall()
    st.dataframe([dict(zip(["ID","법령명","법령ID","URL","요약","전달문","상태","등록일"],r)) for r in rows],use_container_width=True)
    wb=Workbook();ws=wb.active;ws.title="법령 관리대장"
    ws.append(["ID","법령명","법령ID","URL","요약","전달문","상태","등록일"])
    for r in rows:ws.append(list(r))
    buf=io.BytesIO();wb.save(buf)
    st.download_button("엑셀 관리대장 다운로드",data=buf.getvalue(),file_name="법령관리대장.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
