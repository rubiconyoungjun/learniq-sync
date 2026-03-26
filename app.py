import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

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
        st.error(f"파일을 읽는 중 오류 발생: {e}")
        return None

# --- 사이드바: 파일 업로드 ---
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일 (회원 그룹 포함)", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 (상품명 포함)", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        with st.spinner('기관별 데이터를 매칭 중...'):
            # 1. 회원 데이터 정리
            # 이미지에서 확인한 '회원 그룹', '이름', '아이디(이메일)', '로그인' 컬럼명 대응
            df_m = pd.DataFrame()
            df_m['소속기관'] = df_m_raw['회원 그룹'].fillna('일반회원')
            df_m['이름'] = df_m_raw['이름'].fillna('이름없음')
            df_m['이메일'] = df_m_raw['아이디'].fillna(df_m_raw.get('이메일', '')) # 아이디가 이메일인 경우 대응
            df_m['가입일'] = df_m_raw['가입일'].fillna('-')
            df_m['로그인 횟수'] = df_m_raw['로그인'].fillna(0)
            
            # 2. 주문 데이터 정리 (한 명당 여러 강좌를 콤마로 합침)
            # 주문 내역의 '주문자 이메일'과 '상품명' 컬럼 사용
            o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '이메일'
            o_prod_col = '상품명'
            
            if o_email_col in df_o_raw.columns and o_prod_col in df_o_raw.columns:
                df_o_clean = df_o_raw.groupby(o_email_col)[o_prod_col].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_clean.columns = ['이메일', '주문 강좌']
                
                # 3. 데이터 병합 (회원 목록 기준)
                df_final = pd.merge(df_m, df_o_clean, on='이메일', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
                
                # --- UI 출력 ---
                tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 기관별 통계"])
                
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("조회할 소속기관(회원 그룹) 선택", groups)
                    
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    # 요청하신 5대 컬럼 출력
                    display_cols = ['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']
                    st.subheader(f"📍 {sel_group} 수강 현황")
                    st.dataframe(view_df[display_cols], use_container_width=True)
                    
                    # 다운로드 버튼
                    csv = view_df[display_cols].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 현재 리스트 다운로드 (CSV)", csv, f"{sel_group}_현황.csv", "text/csv")

                with tab2:
                    st.subheader("🏢 기관별 인원 요약")
                    summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                    summary.columns = ['소속기관', '인원수(명)']
                    st.table(summary)
            else:
                st.error("주문 내역 파일에서 '주문자 이메일' 또는 '상품명' 컬럼을 찾을 수 없습니다.")
else:
    st.info("사이드바에 아임웹에서 다운로드한 '회원 목록'과 '주문 내역' 파일을 각각 업로드해주세요.")
