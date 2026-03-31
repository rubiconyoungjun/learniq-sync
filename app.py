import streamlit as st
import pandas as pd

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
    "기관 선택",
    "연세대학교 미래캠퍼스",
    "연세대학교 신촌/국제캠퍼스",
    "KAIST",
    "목원대학교",
    "공주대학교",
    "국립중앙도서관",
    "국립세종도서관"
]
selected_org = st.sidebar.selectbox("대상 기관을 선택하세요", org_options)
file_m = st.sidebar.file_uploader(f"[{selected_org}] 회원 목록 업로드", type=['csv', 'xlsx'])

if file_o and file_m and selected_org != "기관 선택":
    df_o_raw = load_data(file_o)
    df_m_raw = load_data(file_m)
    
    if df_o_raw is not None and df_m_raw is not None:
        # 컬럼 정리
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

        # --- [Step 2] 회원 데이터 전처리 (선택한 기관명 주입) ---
        # 이메일 매칭을 위한 회원 정보
        df_member = df_m_raw.copy()
        
        # 드롭다운에서 선택한 기관명을 '소속기관' 컬럼으로 강제 지정 (AI- 등 정제 필요 없음)
        df_member['소속기관'] = selected_org
        
        # 가져올 추가 회원 정보 리스트
        m_cols_to_fetch = [
            '이메일', '소속기관', '고유키', '아이디', '이용자 유형', 
            '가입일', '로그인 횟수', '마지막 로그인', '구매횟수(KRW)'
        ]
        available_m = [c for c in m_cols_to_fetch if c in df_member.columns]
        df_m_subset = df_member[available_m].copy()
        df_m_subset = df_m_subset.rename(columns={'구매횟수(KRW)': '강좌 신청 횟수'})

        # --- [Step 3] 데이터 병합 (이메일 기준) ---
        df_master['match_key'] = df_master['이메일'].astype(str).str.strip().str.lower()
        df_m_subset['match_key'] = df_m_subset['이메일'].astype(str).str.strip().str.lower()

        # 주문을 기준으로 회원 정보 매칭
        df_final = pd.merge(
            df_master, 
            df_m_subset.drop(columns=['이메일']), 
            on='match_key', 
            how='left'
        )

        # 매칭 실패 건 처리 (선택한 기관 소속이 아닌 주문들)
        df_final = df_final.drop(columns=['match_key']).fillna("-")

        # --- [Step 4] 화면 출력 ---
        st.success(f"✅ [{selected_org}] 데이터 매칭이 완료되었습니다.")
        
        # 지표 요약
        col1, col2 = st.columns(2)
        matched_count = len(df_final[df_final['소속기관'] == selected_org])
        col1.metric("전체 주문 건수", f"{len(df_master)}건")
        col2.metric(f"{selected_org} 매칭 건수", f"{matched_count}건")

        # 결과 테이블
        st.subheader(f"📋 {selected_org} 통합 수강 리스트")
        # 해당 기관 데이터만 모아보기 혹은 전체 보기 선택 가능
        view_option = st.radio("보기 설정", ["전체 주문 보기", f"{selected_org} 소속만 보기"], horizontal=True)
        
        if "소속만 보기" in view_option:
            display_df = df_final[df_final['소속기관'] == selected_org]
        else:
            display_df = df_final

        st.dataframe(display_df.astype(str), use_container_width=True, hide_index=True)

        # 다운로드
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 {selected_org} 리포트 다운로드",
            data=csv,
            file_name=f"LearnIQ_{selected_org}_Report.csv"
        )
else:
    st.info("💡 왼쪽 사이드바에서 **[공통 주문 내역]**을 업로드한 후, **[기관 선택]** 및 **[회원 목록]**을 업로드해 주세요.")
