import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏢 LearnIQ 기관별 통합 수강 관리 시스템")

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

# --- 사이드바 인터페이스 ---
st.sidebar.header("📁 데이터 업로드 세팅")

# 1. 주문 내역 (공통)
st.sidebar.subheader("1. 공통 주문 내역")
file_o = st.sidebar.file_uploader("주문 내역(Master) 업로드", type=['csv', 'xlsx'])

st.sidebar.markdown("---")

# 2. 기관 선택 및 회원 목록 업로드
st.sidebar.subheader("2. 기관별 회원 목록")
org_options = [
    "기관 선택", "연세대학교 미래캠퍼스", "연세대학교 신촌/국제캠퍼스", 
    "KAIST", "목원대학교", "공주대학교", "국립중앙도서관", "국립세종도서관"
]
selected_org = st.sidebar.selectbox("대상 기관을 선택하세요", org_options)
file_m = st.sidebar.file_uploader(f"[{selected_org}] 회원 목록 업로드", type=['csv', 'xlsx'])

if file_o and file_m and selected_org != "기관 선택":
    df_o_raw = load_data(file_o)
    df_m_raw = load_data(file_m)
    
    if df_o_raw is not None and df_m_raw is not None:
        # 컬럼 공백 제거
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]

        # --- [Step 1] 주문 데이터(Master) 전처리 ---
        rename_o_dict = {
            '주문자 이름': '성명',
            '주문자 이메일': '이메일',
            '주문자 번호': '학번(입력번호)',
            '상품명': '강좌명',
            '주문일': '강좌 신청일'
        }
        df_master = df_o_raw[list(rename_o_dict.keys())].copy().rename(columns=rename_o_dict)

       # --- [Step 2] 회원 데이터 전처리 및 매칭 키 생성 ---
df_member = df_m_raw.copy()
df_member['소속기관'] = selected_org

# 회원 목록에서 '성명' 또는 '이름' 컬럼 찾기
if '성명' in df_member.columns:
    m_name_col = '성명'
elif '이름' in df_member.columns:
    m_name_col = '이름'
else:
    st.error("⚠️ 회원 목록에 '성명' 또는 '이름' 컬럼이 없습니다. 컬럼명을 확인해주세요.")
    st.stop()

# 이메일 + 성명 복합 매칭 키 생성 함수 (에러 방지용)
def create_match_key(df, email_col, name_col):
    return (df[email_col].astype(str).str.strip().str.lower() + "_" + 
            df[name_col].astype(str).str.strip())

# 주문 데이터와 회원 데이터 각각에 매칭 키 생성
df_master['match_key'] = create_match_key(df_master, '이메일', '성명')
df_member['match_key'] = create_match_key(df_member, '이메일', m_name_col)

# 가져올 상세 정보 리스트 (회원 목록에 실제 존재하는 컬럼만 추출)
m_cols_to_fetch = [
    'match_key', '소속기관', '고유키', '아이디', '이용자 유형', 
    '가입일', '로그인 횟수', '마지막 로그인', '구매횟수(KRW)'
]
available_m = [c for c in m_cols_to_fetch if c in df_member.columns]
df_m_subset = df_member[available_m].copy()

# '구매횟수(KRW)' 컬럼이 있으면 이름 변경
if '구매횟수(KRW)' in df_m_subset.columns:
    df_m_subset = df_m_subset.rename(columns={'구매횟수(KRW)': '강좌 신청 횟수'})

        # --- [Step 3] 데이터 병합 (이메일 & 성명 동시 매칭) ---
        # 중복 방지를 위해 회원 정보의 매칭 키 중복 제거 (첫 번째 값 기준)
        df_m_subset = df_m_subset.drop_duplicates(subset=['match_key'])
        
        df_final = pd.merge(
            df_master, 
            df_m_subset, 
            on='match_key', 
            how='left'
        )

        # 사용 후 매칭 키 삭제 및 결측치 처리
        df_final = df_final.drop(columns=['match_key']).fillna("-")

        # --- [Step 4] 화면 출력 및 지표 ---
        st.success(f"✅ [{selected_org}] 데이터 매칭 및 시각화가 완료되었습니다.")
        
        col1, col2, col3 = st.columns(3)
        matched_df = df_final[df_final['소속기관'] == selected_org]
        col1.metric("전체 주문 건수", f"{len(df_master)}건")
        col2.metric(f"{selected_org} 매칭", f"{len(matched_df)}건")
        col3.metric("매칭률", f"{(len(matched_df)/len(df_master)*100):.1f}%")

        # --- [Step 5] 강좌별 수강 횟수 시각화 (Plotly) ---
        st.markdown("---")
        st.subheader("📊 강좌별 수강 현황 통계")
        
        # 해당 기관 수강 데이터 기반 통계
        course_stats = matched_df['강좌명'].value_counts().reset_index()
        course_stats.columns = ['강좌명', '수강횟수']

        if not course_stats.empty:
            fig = px.bar(course_stats, x='수강횟수', y='강좌명', 
                         orientation='h',
                         title=f"[{selected_org}] 강좌별 수강 인기 순위",
                         text='수강횟수',
                         color='수강횟수',
                         color_continuous_scale='Blues')
            
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("시각화할 매칭 데이터가 없습니다.")

        # --- [Step 6] 결과 테이블 및 다운로드 ---
        st.markdown("---")
        st.subheader(f"📋 {selected_org} 통합 수강 리스트")
        view_option = st.radio("보기 설정", ["전체 주문 보기", f"{selected_org} 소속만 보기"], horizontal=True)
        
        display_df = matched_df if "소속만 보기" in view_option else df_final
        st.dataframe(display_df.astype(str), use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 {selected_org} 리포트 다운로드",
            data=csv,
            file_name=f"LearnIQ_{selected_org}_Report.csv"
        )
else:
    st.info("💡 왼쪽 사이드바에서 **[공통 주문 내역]**을 업로드한 후, **[기관 선택]** 및 **[회원 목록]**을 업로드해 주세요.")
