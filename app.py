import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 강좌 수강 분석")

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
        # 컬럼 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # --- 1. 회원 데이터 전처리 (정확한 분리) ---
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        df_m['이메일'] = df_m['이메일'].astype(str).str.strip().str.lower() # 소문자 통일
        
        # 콤마로 구분된 그룹을 개별 행으로 분리 (정확한 매칭의 핵심)
        df_m['소속기관'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_m = df_m.explode('소속기관')
        df_m['소속기관'] = df_m['소속기관'].str.strip() # 앞뒤 공백 제거
        
        # 특정 제외 패턴 처리 (AI-PPT, AI-Literacy 등)
        exclude_prefixes = ('AI-PPT', 'AI-Literacy', 'nan', '-', 'None')
        df_m = df_m[~df_m['소속기관'].str.startswith(exclude_prefixes)]
        df_m = df_m[df_m['소속기관'] != ""]

        # --- 2. 주문 데이터 전처리 ---
        df_o = df_o_raw[['주문자 이메일', '상품명', '주문일', '주문상태']].copy()
        df_o['주문자 이메일'] = df_o['주문자 이메일'].astype(str).str.strip().str.lower() # 소문자 통일

        # --- 3. 데이터 병합 (Merge) ---
        # 한 명의 회원이 N개 기관에 속해 있다면 주문 데이터도 N개로 복제되어 각 기관 통계에 잡히게 됩니다.
        df_final = pd.merge(
            df_o, 
            df_m, 
            left_on='주문자 이메일', 
            right_on='이메일', 
            how='inner' # 회원 정보가 있는 주문만 분석 (기관 분석용)
        )

        # --- 4. 대시보드 UI ---
        # 사이드바 기관 필터
        all_orgs = sorted(df_final['소속기관'].unique().tolist())
        selected_org = st.sidebar.selectbox("🔍 분석할 기관 선택", ["전체"] + all_orgs)

        if selected_org != "전체":
            display_df = df_final[df_final['소속기관'] == selected_org]
        else:
            display_df = df_final

        # 상단 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("분석된 주문 건수", f"{len(display_df)}건")
        c2.metric("수강 인원(중복제외)", f"{display_df['주문자 이메일'].nunique()}명")
        c3.metric("선택 기관", selected_org)

        tab1, tab2 = st.tabs(["📊 기관별 강좌 분석", "📋 상세 수강생 명단"])

        with tab1:
            st.subheader(f"📈 {selected_org} 인기 강좌 순위")
            if not display_df.empty:
                course_stats = display_df['상품명'].value_counts().reset_index()
                course_stats.columns = ['강좌명', '수강건수']
                
                fig = px.bar(course_stats.head(15), x='수강건수', y='강좌명', 
                             orientation='h', text_auto=True,
                             color='수강건수', color_continuous_scale='Blues')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("데이터가 없습니다.")

        with tab2:
            st.subheader(f"👥 {selected_org} 상세 리스트")
            st.dataframe(
                display_df[['소속기관', '이름', '주문자 이메일', '상품명', '주문일']].sort_values(by='이름'),
                use_container_width=True, hide_index=True
            )

else:
    st.info("사이드바에서 '회원 목록'과 '주문 내역' 파일을 업로드해 주세요.")
