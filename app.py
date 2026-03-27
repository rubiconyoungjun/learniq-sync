import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync 통합 관리 대시보드")

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

st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 (xlsx/csv)", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 (xlsx/csv)", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # 1. 회원 정보 정리 (매칭용)
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        df_m['이메일'] = df_m['이메일'].astype(str).str.strip()
        # '회원 그룹' 컬럼명을 '소속기관'으로 미리 변경
        df_m = df_m.rename(columns={'회원 그룹': '소속기관'})
        
        # 2. 주문 정보 정리 (491건 기준)
        df_o = df_o_raw.copy()
        df_o['주문자 이메일'] = df_o['주문자 이메일'].astype(str).str.strip()

        # 3. 데이터 병합 (주문자 이메일 == 회원 이메일)
        df_merged = pd.merge(
            df_o, 
            df_m, 
            left_on='주문자 이메일', 
            right_on='이메일', 
            how='left'
        )

        # 회원 목록에 없는 경우 처리
        df_merged['소속기관'] = df_merged['소속기관'].fillna("미가입/정보없음")
        df_merged['이름'] = df_merged['이름'].fillna(df_merged['주문자 이름'])

        # 4. 소속기관(그룹) 분리 로직 (콤마 대응)
        df_merged['소속기관'] = df_merged['소속기관'].astype(str).str.split(',')
        df_display = df_merged.explode('소속기관')
        df_display['소속기관'] = df_display['소속기관'].str.strip()

        # 5. 특정 그룹 제외 필터 (AI-PPT, AI-Literacy)
        exclude_prefixes = ('AI-PPT', 'AI-Literacy')
        all_groups = sorted([g for g in df_display['소속기관'].unique() if g not in ["nan", "-", "None", "미가입/정보없음"]])
        clean_groups = [g for g in all_groups if not g.startswith(exclude_prefixes)]
        
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 필터링", ["전체(누락없음)"] + clean_groups)

        # 필터 적용
        if selected_group == "전체(누락없음)":
            filtered_df = df_display
        else:
            filtered_df = df_display[df_display['소속기관'] == selected_group]

        # [통계]
        st.sidebar.markdown("---")
        st.sidebar.write(f"📊 원본 주문: {len(df_o_raw)}건")
        st.sidebar.write(f"👥 매칭 성공: {len(df_merged[df_merged['이메일'].notnull()])}건")

        # [탭 구성]
        tab1, tab2 = st.tabs(["📋 주문-회원 매칭 명단", "📊 강좌별 분석"])

        with tab1:
            st.subheader("💡 '소속기관'은 회원 목록의 그룹 정보를 바탕으로 표시됩니다.")
            # 화면에 보여줄 컬럼 설정 (회원 그룹 대신 '소속기관' 사용)
            cols_to_show = ['주문일', '이름', '주문자 이메일', '소속기관', '상품명', '주문상태']
            st.dataframe(filtered_df[cols_to_show].astype(str), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("📈 인기 강좌 순위")
            course_counts = filtered_df['상품명'].value_counts().head(20).reset_index()
            course_counts.columns = ['강좌명', '판매수']
            fig = px.bar(course_counts, x='판매수', y='강좌명', orientation='h', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("사이드바에서 두 파일을 업로드해 주세요.")
