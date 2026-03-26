import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# 파일 로더 함수 (엔진 명시)
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            try: return pd.read_csv(file, encoding='utf-8-sig')
            except: return pd.read_csv(file, encoding='cp949')
        elif file.name.endswith('.xlsx'):
            # openpyxl 엔진을 명시적으로 지정
            return pd.read_excel(file, engine='openpyxl')
        elif file.name.endswith('.xls'):
            # 구버전 엑셀 엔진 지정
            return pd.read_excel(file, engine='xlrd')
    except Exception as e:
        st.error(f"파일을 읽는 중 오류 발생: {e}")
        st.info("requirements.txt 파일에 'openpyxl'이 포함되어 있는지 확인해 주세요.")
        return None

# --- 사이드바: 파일 업로드 ---
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일 (회원 그룹 포함)", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 (상품명 포함)", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        with st.spinner('데이터 매칭 중...'):
            # 1. 회원 데이터 정리 ('회원 그룹'을 소속기관으로 설정)
            df_m = pd.DataFrame()
            # 파일 내 실제 컬럼명과 일치시키기 위해 .strip() 사용
            df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
            
            df_m['소속기관'] = df_m_raw['회원 그룹'].fillna('일반회원')
            df_m['이름'] = df_m_raw['이름'].fillna('이름없음')
            # 아이디 컬럼을 이메일 매칭용으로 사용
            df_m['이메일'] = df_m_raw['아이디'].astype(str).str.strip()
            df_m['가입일'] = df_m_raw['가입일'].fillna('-')
            df_m['로그인 횟수'] = df_m_raw['로그인'].fillna(0)
            
            # 2. 주문 데이터 정리
            df_o_raw.columns = [c.strip() for c in df_o_raw.columns]
            o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '이메일'
            
            if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                # 이메일 공백 제거 후 매칭 준비
                df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                
                # 한 명의 여러 주문 강좌를 콤마로 합치기
                df_o_clean = df_o_raw.groupby(o_email_col)['상품명'].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_clean.columns = ['이메일', '주문 강좌']
                
                # 3. 데이터 병합
                df_final = pd.merge(df_m, df_o_clean, on='이메일', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
                
                # --- 화면 출력 ---
                tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 기관별 통계"])
                
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("조회할 소속기관(회원 그룹) 선택", groups)
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    display_cols = ['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']
                    st.dataframe(view_df[display_cols], use_container_width=True)
                    
                    csv = view_df[display_cols].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 현재 결과 다운로드 (CSV)", csv, f"{sel_group}_현황.csv")

                with tab2:
                    summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                    summary.columns = ['소속기관', '인원수(명)']
                    st.table(summary)
            else:
                st.error("주문 파일에 '주문자 이메일' 혹은 '상품명' 컬럼이 없습니다.")
else:
    st.info("사이드바에 회원 목록과 주문 내역 파일을 업로드해 주세요.")
