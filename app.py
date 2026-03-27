import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 강좌 수강 분석 (정밀 매칭)")

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

        # --- 1. 회원 데이터 전처리 ---
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        # 이메일 매칭률을 높이기 위해 소문자화 및 공백 제거
        df_m['match_email'] = df_m['이메일'].astype(str).str.strip().str.lower()
        
        # 회원 그룹 전처리 (기관별 분석을 위해 분리)
        df_m['소속기관'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_m = df_m.explode('소속기관')
        df_m['소속기관'] = df_m['소속기관'].str.strip()
        
        # 제외 패턴 적용 (필터링)
        exclude_prefixes = ('AI-PPT', 'AI-Literacy', 'nan', '-', 'None', '')
        df_m = df_m[~df_m['소속기관'].str.startswith(exclude_prefixes)]
        # 소속기관이 비어버린 경우 '일반회원' 혹은 '기타'로 표시
        df_m['소속기관'] = df_m['소속기관'].replace('', '기타/미지정')

        # --- 2. 주문 데이터 전처리 ---
        df_o = df_o_raw.copy()
        df_o['match_email'] = df_o['주문자 이메일'].astype(str).str.strip().str.lower()

        # --- 3. 데이터 병합 (주문 491건을 무조건 유지하는 Left Join) ---
        # 주문(Left)을 기준으로 회원(Right)을 붙입니다.
        df_final = pd.merge(
            df_o, 
            df_m[['match_email', '소속기관', '이름']], 
            on='match_email', 
            how='left'
        )

        # 회원 목록에 없어서 소속기관이 매칭 안 된 경우 처리
        df_final['소속기관'] = df_final['소속기관'].fillna("미가입/기타")
        df_final['이름'] = df_final['이름'].fillna(df_final['주문자 이름'])

        # --- 4. 대시보드 UI ---
        # 사이드바 기관 필터
        all_orgs = sorted(df_final['소속기관'].unique().tolist())
        selected_org = st.sidebar.selectbox("🔍 분석할 기관 선택", ["전체(491건)"] + all_orgs)

        if selected_org != "전체(491건)":
            display_df = df_final[df_final['소속기관'] == selected_org]
        else:
            display_df = df_final

        # 상단 핵심 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("총 주문 건수", f"{len(df_o_raw)}건") # 항상 491건 근처가 나와야 함
        c2.metric("조회된 데이터 수", f"{len(display_df)}건")
        c3.metric("매칭 성공 인원", f"{df_final[df_final['소속기관'] != '미가입/기타']['주문자 이메일'].nunique()}명")

        tab1, tab2 = st.tabs(["📊 강좌 수강 분석", "📋 상세 내역"])

        with tab1:
            st.subheader(f"📈 {selected_org} 인기 강좌 순위")
            if not display_df.empty:
                # 상품명별 카운트
                course_stats = display_df['상품명'].value_counts().reset_index()
                course_stats.columns = ['강좌명', '수강건수']
                
                fig = px.bar(course_stats.head(20), x='수강건수', y='강좌명', 
                             orientation='h', text_auto=True,
                             color='수강건수', color_continuous_scale='Viridis')
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("데이터가 없습니다.")

        with tab2:
            st.subheader("📑 상세 수강생 명단")
            # 필요한 컬럼만 정리해서 출력
            show_cols = ['주문일', '소속기관', '이름', '주문자 이메일', '상품명', '주문상태']
            st.dataframe(display_df[show_cols].astype(str), use_container_width=True, hide_index=True)

else:
    st.info("사이드바에서 '회원 목록'과 '주문 내역' 파일을 업로드해 주세요.")
