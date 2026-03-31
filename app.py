import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 강좌 수강 분석 시스템")

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

# 1. 사이드바: 데이터 업로드
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일 (회원2026...)", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 (기본_양식...)", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼명 앞뒤 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # --- 2. 회원 데이터 전처리 (Key: 이메일) ---
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        # 매칭 정확도를 위해 소문자 변환 및 공백 제거
        df_m['key_email'] = df_m['이메일'].astype(str).str.strip().str.lower()
        
        # 회원 그룹 분리 및 'AI-' 제거 로직
        df_m['소속기관'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_m = df_m.explode('소속기관')
        df_m['소속기관'] = df_m['소속기관'].str.strip()
        
        # 'AI-'로 시작하는 그룹 및 무의미한 값 제외
        exclude_list = ('AI-', 'ai-', 'nan', '-', 'None')
        df_m = df_m[~df_m['소속기관'].str.startswith(exclude_list)]
        df_m = df_m[df_m['소속기관'] != ""]

        # --- 3. 주문 데이터 전처리 (Key: 주문자 이메일) ---
        df_o = df_o_raw.copy()
        df_o['key_email'] = df_o['주문자 이메일'].astype(str).str.strip().str.lower()

        # --- 4. 데이터 연결 (Left Join: 주문 491건 기준) ---
        # 
        df_final = pd.merge(
            df_o, 
            df_m[['key_email', '소속기관', '이름']], 
            on='key_email', 
            how='left'
        )

        # 매칭되지 않은 경우(미가입자 또는 AI 그룹만 있던 경우) 처리
        df_final['소속기관'] = df_final['소속기관'].fillna("일반/기타")
        df_final['이름_매칭'] = df_final['이름'].fillna(df_final['주문자 이름'])

        # --- 5. 대시보드 화면 구성 ---
        # 사이드바: 기관 필터링 (AI-가 빠진 순수 기관 목록)
        org_list = sorted([g for g in df_final['소속기관'].unique() if g != "일반/기타"])
        selected_org = st.sidebar.selectbox("🔍 분석할 기관 선택", ["전체(누락없음)"] + org_list)

        if selected_org != "전체(누락없음)":
            display_df = df_final[df_final['소속기관'] == selected_org]
        else:
            display_df = df_final

        # 상단 지표
        m1, m2, m3 = st.columns(3)
        m1.metric("총 주문 건수", f"{len(df_o_raw)}건")
        m2.metric("조회된 분석 건수", f"{len(display_df)}건")
        m3.metric("매칭된 인원(중복제외)", f"{display_df['key_email'].nunique()}명")

        tab1, tab2 = st.tabs(["📊 기관별 강좌 분석", "📋 상세 수강 명단"])

        with tab1:
            st.subheader(f"📈 {selected_org} 인기 강좌 TOP 20")
            if not display_df.empty:
                course_counts = display_df['상품명'].value_counts().reset_index()
                course_counts.columns = ['강좌명', '주문수']
                
                fig = px.bar(course_counts.head(20), x='주문수', y='강좌명', 
                             orientation='h', text_auto=True,
                             color='주문수', color_continuous_scale='Turbo')
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("분석할 데이터가 없습니다.")

        with tab2:
            st.subheader("📑 상세 매칭 내역")
            # 보기 편하게 컬럼 순서 조정
            view_cols = ['주문일', '소속기관', '이름_매칭', '주문자 이메일', '상품명', '주문상태']
            st.dataframe(display_df[view_cols].astype(str), use_container_width=True, hide_index=True)

else:
    st.info("💡 사이드바에서 두 파일을 업로드하면 분석이 시작됩니다.")
