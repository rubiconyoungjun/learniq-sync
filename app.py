import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync 통합 관리 대시보드")

# 1. 파일 읽기 함수 정의
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

# 2. 사이드바 파일 업로드 (이 부분이 있어야 NameError가 안 납니다)
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (xlsx/csv)", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (xlsx/csv)", type=['csv', 'xlsx'])

# 3. 메인 로직 시작
if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # [회원 정보 정리]
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        df_m['이메일'] = df_m['이메일'].astype(str).str.strip()
        
        # [주문 정보 정리] 원본 491건을 기준으로 삼기 위해 필요한 컬럼만 추출
        # '주문자 이메일'이 기준입니다.
        df_o = df_o_raw.copy()
        df_o['주문자 이메일'] = df_o['주문자 이메일'].astype(str).str.strip()

        # [데이터 병합] how='left'를 사용하여 주문 내역 491건을 무조건 유지
        df_merged = pd.merge(
            df_o, 
            df_m, 
            left_on='주문자 이메일', 
            right_on='이메일', 
            how='left'
        )

        # 정보가 없는 경우 빈칸 채우기
        df_merged['회원 그룹'] = df_merged['회원 그룹'].fillna("미가입/그룹없음")
        df_merged['이름'] = df_merged['이름'].fillna(df_merged['주문자 이름'])

        # [회원 그룹 분리] 콤마로 된 그룹 쪼개기
        df_merged['회원 그룹'] = df_merged['회원 그룹'].astype(str).str.split(',')
        df_display = df_merged.explode('회원 그룹')
        df_display['회원 그룹'] = df_display['회원 그룹'].str.strip()

        # [필터링 설정]
        # AI-PPT, AI-Literacy로 시작하는 그룹은 사이드바 목록에서만 숨깁니다.
        exclude_prefixes = ('AI-PPT', 'AI-Literacy')
        all_groups = sorted([g for g in df_display['회원 그룹'].unique() if g not in ["nan", "-", "None", "미가입/그룹없음"]])
        clean_groups = [g for g in all_groups if not g.startswith(exclude_prefixes)]
        
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 필터링", ["전체(누락없음)"] + clean_groups)

        # 필터 적용
        if selected_group == "전체(누락없음)":
            filtered_df = df_display
        else:
            filtered_df = df_display[df_display['회원 그룹'] == selected_group]

        # [통계 지표 표시]
        c1, c2, c3 = st.columns(3)
        c1.metric("총 주문 건수 (원본)", f"{len(df_o_raw)}건")
        c2.metric("현재 매칭된 데이터", f"{len(filtered_df)}건")
        c3.metric("선택된 기관", selected_group)

        # [탭 구성]
        tab1, tab2 = st.tabs(["📋 주문-회원 매칭 명단", "📊 강좌별 분석"])

        with tab1:
            st.subheader("💡 주문 이메일과 회원 정보를 대조한 결과입니다.")
            cols_to_show = ['주문일', '이름', '주문자 이메일', '회원 그룹', '상품명', '주문상태']
            st.dataframe(filtered_df[cols_to_show].astype(str), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("📈 많이 판매된 강좌 순위")
            course_counts = filtered_df['상품명'].value_counts().head(20).reset_index()
            course_counts.columns = ['강좌명', '판매수']
            fig = px.bar(course_counts, x='판매수', y='강좌명', orientation='h', text_auto=True, color='판매수')
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("사이드바에서 '회원 목록'과 '주문 내역' 두 파일을 모두 업로드하면 분석이 시작됩니다.")
