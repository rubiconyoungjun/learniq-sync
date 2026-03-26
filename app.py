import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 리포트")

# 파일 로더 함수
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
        st.error(f"파일 읽기 오류: {e}")
        return None

# 사이드바: 파일 업로드
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (xlsx/csv/xls)", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (xlsx/csv/xls)", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼명 앞뒤 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        with st.spinner('데이터를 매칭 중입니다...'):
            # 1. 회원 데이터 정리
            df_m = pd.DataFrame()
            # '회원 그룹'을 소속기관으로, '아이디'를 매칭 키로 사용
            df_m['소속기관'] = df_m_raw['회원 그룹'].fillna('일반회원')
            df_m['이름'] = df_m_raw['이름'].fillna('이름없음')
            df_m['아이디'] = df_m_raw['아이디'].astype(str).str.strip()
            df_m['가입일'] = df_m_raw['가입일'].fillna('-')
            df_m['로그인 횟수'] = df_m_raw['로그인'].fillna(0)

            # 2. 주문 데이터 정리
            # '주문자 이메일' 컬럼이 회원목록의 '아이디'와 매칭됨
            o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '아이디'
            
            if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                
                # 강좌명 합치기 (중복 제거 후 콤마 구분)
                df_o_summary = df_o_raw.groupby(o_email_col)['상품명'].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_summary.columns = ['아이디', '주문 강좌']
                
                # 3. 데이터 병합
                df_final = pd.merge(df_m, df_o_summary, on='아이디', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")

                # --- 결과 출력 ---
                tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 기관별 통계"])
                
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("소속기관 선택", groups)
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    st.dataframe(view_df[['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']], use_container_width=True)
                    
                    csv = view_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 결과 다운로드 (CSV)", csv, f"{sel_group}_현황.csv")

                with tab2:
                    summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                    fig = px.bar(summary, x='소속기관', y='이름', text_auto=True, title="기관별 수강 인원")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("주문 파일에 '주문자 이메일' 또는 '상품명' 컬럼이 없습니다.")
else:
    st.info("사이드바에서 '회원 목록'과 '주문 내역' 파일을 업로드해주세요.")
