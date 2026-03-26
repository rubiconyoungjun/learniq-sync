import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# 파일 로드 함수 (엔진을 명시적으로 처리)
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            try: return pd.read_csv(file, encoding='utf-8-sig')
            except: return pd.read_csv(file, encoding='cp949')
        elif file.name.endswith('.xlsx'):
            # openpyxl 엔진이 없으면 여기서 에러가 발생함
            return pd.read_excel(file, engine='openpyxl')
        elif file.name.endswith('.xls'):
            return pd.read_excel(file, engine='xlrd')
    except Exception as e:
        st.error(f"⚠️ 파일 읽기 오류: {e}")
        st.warning("💡 해결 방법: 'requirements.txt' 파일에 'openpyxl' 문구가 정확히 들어있는지 확인하고 GitHub에 다시 Push해 주세요.")
        return None

# 사이드바 설정
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (xlsx/csv)", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (xlsx/csv)", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        with st.spinner('데이터 매칭 중...'):
            # 컬럼명 공백 제거
            df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
            df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

            # 1. 회원 데이터 정리 ('회원 그룹' 사용)
            df_m = pd.DataFrame()
            if '회원 그룹' in df_m_raw.columns:
                df_m['소속기관'] = df_m_raw['회원 그룹'].fillna('일반회원')
            else:
                df_m['소속기관'] = '그룹컬럼없음'
                st.error("'회원 목록' 파일에 '회원 그룹' 컬럼이 보이지 않습니다.")

            df_m['이름'] = df_m_raw.get('이름', '이름없음')
            df_m['아이디'] = df_m_raw.get('아이디', '').astype(str).str.strip()
            df_m['가입일'] = df_m_raw.get('가입일', '-')
            df_m['로그인 횟수'] = df_m_raw.get('로그인', 0)

            # 2. 주문 데이터 정리 (아이디 매칭용)
            # 주문 내역의 '주문자 이메일'이 회원 목록의 '아이디'와 매칭된다고 가정
            o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '이메일'
            
            if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                
                # 강좌 합치기 (콤마 구분)
                df_o_clean = df_o_raw.groupby(o_email_col)['상품명'].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_clean.columns = ['아이디', '주문 강좌']
                
                # 3. 최종 병합
                df_final = pd.merge(df_m, df_o_clean, on='아이디', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
                
                # 결과 출력
                tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 기관 요약"])
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("기관(회원 그룹) 선택", groups)
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    st.dataframe(view_df[['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']], use_container_width=True)
                with tab2:
                    st.table(df_final.groupby('소속기관')['이름'].count().reset_index().rename(columns={'이름':'인원'}))
            else:
                st.error("주문 파일 형식이 맞지 않습니다 ('주문자 이메일' 또는 '상품명' 컬럼 필요).")
