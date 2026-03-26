import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# 파일 로드 함수 (엑셀 엔진 명시)
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            try: return pd.read_csv(file, encoding='utf-8-sig')
            except: return pd.read_csv(file, encoding='cp949')
        elif file.name.endswith('.xlsx'):
            return pd.read_excel(file, engine='openpyxl')
        elif file.name.endswith('.xls'):
            return pd.read_excel(file, engine='xlrd')
    except Exception as e:
        st.error(f"⚠️ 파일 읽기 오류: {e}")
        return None

# 사이드바 설정
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (회원 그룹 포함)", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (상품명 포함)", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼명 앞뒤 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        with st.spinner('데이터 분석 중...'):
            # 1. 회원 데이터 정리
            df_m = pd.DataFrame()
            # 파일 내 실제 컬럼명인 '회원 그룹', '아이디', '이름' 등을 매칭
            df_m['소속기관'] = df_m_raw['회원 그룹'].fillna('일반회원')
            df_m['이름'] = df_m_raw.get('이름', '이름없음')
            df_m['아이디'] = df_m_raw.get('아이디', '').astype(str).str.strip()
            df_m['가입일'] = df_m_raw.get('가입일', '-')
            
            # 2. 주문 데이터 정리
            # '주문자 이메일' 컬럼이 회원목록의 '아이디'와 매칭된다고 가정
            o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '이메일'
            
            if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                
                # 강좌 합치기
                df_o_summary = df_o_raw.groupby(o_email_col)['상품명'].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_summary.columns = ['아이디', '주문 강좌']
                
                # 3. 합치기
                df_final = pd.merge(df_m, df_o_summary, on='아이디', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")

                # 결과 출력
                tab1, tab2 = st.tabs(["📋 상세 명단", "📊 기관별 통계"])
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel = st.selectbox("기관(그룹) 선택", groups)
                    view = df_final if sel == "전체" else df_final[df_final['소속기관'] == sel]
                    st.dataframe(view[['소속기관', '이름', '가입일', '주문 강좌']], use_container_width=True)
                with tab2:
                    summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                    fig = px.bar(summary, x='소속기관', y='이름', text_auto=True, title="기관별 인원수")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("주문 파일에서 '주문자 이메일' 또는 '상품명' 컬럼을 찾을 수 없습니다.")
else:
    st.info("사이드바에 파일을 업로드하면 대시보드가 생성됩니다.")
