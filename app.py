import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 강좌 수강 분석 (정밀 필터링)")

def load_data(file):
    try:
        if file.name.endswith('.csv'):
            try: return pd.read_csv(file, encoding='utf-8-sig')
            except: return pd.read_csv(file, encoding='cp949')
        else:
            return pd.read_excel(file, engine='openpyxl')
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None

# 사이드바 설정
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (xlsx/csv)", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (xlsx/csv)", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼명 정리
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # --- 1. 회원 데이터 전처리 (AI- 제거 로직 강화) ---
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        df_m['match_email'] = df_m['이메일'].astype(str).str.strip().str.lower()
        
        # 콤마로 분리하여 리스트화
        df_m['소속기관'] = df_m['회원 그룹'].astype(str).str.split(',')
        # 리스트를 각각의 행으로 분리 (Explode)
        df_m = df_m.explode('소속기관')
        # 앞뒤 공백 제거
        df_m['소속기관'] = df_m['소속기관'].str.strip()
        
        # 🔥 [핵심] 'AI-'로 시작하는 그룹명 제거 + 기타 불필요한 값 제거
        # 대소문자 구분 없이 'AI-' 또는 'ai-'로 시작하는 것 제외
        df_m = df_m[~df_m['소속기관'].str.startswith(('AI-', 'ai-', 'nan', '-', 'None'))]
        # 빈 문자열 제거
        df_m = df_m[df_m['소속기관'] != ""]

        # --- 2. 주문 데이터 전처리 (491건 전체 유지) ---
        df_o = df_o_raw.copy()
        df_o['match_email'] = df_o['주문자 이메일'].astype(str).str.strip().str.lower()

        # --- 3. 데이터 결합 (Left Join) ---
        # 주문자 이메일을 기준으로 회원 목록의 정보를 가져옵니다.
        df_final = pd.merge(
            df_o, 
            df_m[['match_email', '소속기관', '이름']], 
            on='match_email', 
            how='left'
        )

        # 회원 목록에 없거나 소속기관이 모두 AI- 라서 사라진 경우 처리
        df_final['소속기관'] = df_final['소속기관'].fillna("일반/기타")
        df_final['이름'] = df_final['이름'].fillna(df_final['주문자 이름'])

        # --- 4. 대시보드 UI ---
        # 사이드바 기관 필터 (AI-가 제거된 깨끗한 목록)
        all_orgs = sorted([g for g in df_final['소속기관'].unique() if g != "일반/기타"])
        selected_org = st.sidebar.selectbox("🔍 기관별 강좌 분석", ["전체(491건)"] + all_orgs)

        if selected_org != "전체(491건)":
            display_df = df_final[df_final['소속기관'] == selected_org]
        else:
            display_df = df_final

        # 지표 출력
        c1, c2, c3 = st.columns(3)
        c1.metric("총 주문 건수", f"{len(df_o_raw)}건")
        c2.metric("조회된 분석 데이터", f"{len(display_df)}건")
        c3.metric("선택된 소속기관", selected_org)

        tab1, tab2 = st.tabs(["📊 인기 강좌 분석", "📋 상세 매칭 명단"])

        with tab1:
            st.subheader(f"📈 {selected_org} 내 가장 많이 구매한 강좌")
            if not display_df.empty:
                course_counts = display_df['상품명'].value_counts().reset_index()
                course_counts.columns = ['강좌명', '주문수']
                
                fig = px.bar(course_counts.head(20), x='주문수', y='강좌명', 
                             orientation='h', text_auto=True,
                             color='주문수', color_continuous_scale='Reds')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("분석할 데이터가 없습니다.")

        with tab2:
            st.subheader("📑 주문자별 소속기관 매칭 결과")
            # 요청하신 대로 '회원 그룹'에서 'AI-'를 뺀 값이 '소속기관'으로 나옵니다.
            show_cols = ['주문일', '소속기관', '이름', '주문자 이메일', '상품명', '주문상태']
            st.dataframe(display_df[show_cols].astype(str), use_container_width=True, hide_index=True)

else:
    st.info("사이드바에서 파일을 업로드해 주세요.")
