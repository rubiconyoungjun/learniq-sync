import streamlit as st
import pandas as pd

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync 강좌 수강 현황 대시보드")

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

        # 1. 회원 정보 전처리 (그룹 분리 포함)
        df_m = df_m_raw[['이메일', '이름', '회원 그룹', '고유키']].copy()
        df_m['회원 그룹'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_m = df_m.explode('회원 그룹')
        df_m['회원 그룹'] = df_m['회원 그룹'].str.strip()
        # 특정 그룹 제외 로직 (AI-PPT, AI-Literacy)
        exclude_prefixes = ('AI-PPT', 'AI-Literacy')
        df_m = df_m[~df_m['회원 그룹'].str.startswith(exclude_prefixes)]

        # 2. 주문 정보 전처리 (이메일 매칭용)
        # 주문 파일의 '주문자 이메일' 컬럼 사용
        df_o = df_o_raw[['주문자 이메일', '상품명', '주문일']].copy()
        df_o.columns = ['이메일', '상품명', '주문일']
        df_o['이메일'] = df_o['이메일'].astype(str).str.strip()

        # 3. 데이터 결합 (이메일 기준)
        # 회원 정보에 주문 정보를 붙여서 "어느 기관의 누가 어떤 강좌를 샀는지" 기본판 제작
        df_merged = pd.merge(df_o, df_m, on='이메일', how='inner')

        # 탭 구성
        tab1, tab2 = st.tabs(["📚 강좌별 수강생 명단", "🏛️ 기관별 수강 현황"])

        with tab1:
            st.subheader("📖 강좌별 수강 인원 파악")
            # 강좌 선택 필터
            all_courses = sorted(df_merged['상품명'].unique().tolist())
            selected_course = st.selectbox("조회할 강좌를 선택하세요", all_courses)
            
            course_view = df_merged[df_merged['상품명'] == selected_course]
            st.write(f"**'{selected_course}'** 강좌 수강생: 총 {len(course_view)}명")
            
            # 리스트 표시
            st.dataframe(
                course_view[['이름', '이메일', '회원 그룹', '주문일']].sort_values('이름'),
                use_container_width=True, hide_index=True
            )

        with tab2:
            st.subheader("🏢 소속기관별 수강 강좌 리스트")
            # 기관 선택 필터
            all_groups = sorted([g for g in df_merged['회원 그룹'].unique() if g not in ["nan", "-", "None"]])
            selected_group = st.selectbox("조회할 소속기관을 선택하세요", all_groups)
            
            group_view = df_merged[df_merged['회원 그룹'] == selected_group]
            st.write(f"**'{selected_group}'** 소속 수강 내역: 총 {len(group_view)}건")
            
            # 리스트 표시 (누가 어떤 강좌를 봤는지)
            st.dataframe(
                group_view[['이름', '상품명', '이메일', '주문일']].sort_values(['이름', '주문일']),
                use_container_width=True, hide_index=True
            )
            
            # 추가 분석: 해당 기관에서 가장 인기 있는 강좌
            st.markdown("---")
            st.caption(f"💡 {selected_group} 내 인기 강좌 TOP 5")
            top_courses = group_view['상품명'].value_counts().head(5)
            st.table(top_courses)

else:
    st.info("💡 사이드바에서 '회원 목록'과 '주문 내역' 두 파일을 모두 업로드해 주세요.")
