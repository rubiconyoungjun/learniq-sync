import streamlit as st
import pandas as pd

st.set_page_config(page_title="LearnIQ Data Master", layout="wide")
st.title("📊 LearnIQ 핵심 통합 데이터 조회")

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

# 사이드바: 데이터 업로드
st.sidebar.header("📁 데이터 업로드")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일 (회원2026...)", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 (기본_양식...)", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 1. 컬럼명 정리
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # 2. 회원 엑셀: 요청하신 '꼭 표시해야 할 컬럼'만 선택
        # 이미지에 있던 SNS ID 및 요청하신 제외 항목들은 여기서 누락시킴으로써 필터링합니다.
        essential_m_cols = [
            '고유키', '이메일', '아이디', '회원 그룹', '이름', 
            '학번 (선택사항)', '이용자 유형', '가입일', '로그인 횟수', 
            '마지막 로그인', '최종 로그인 IP', '구매횟수(KRW)'
        ]
        
        # 실제 파일에 해당 컬럼이 있는지 확인 후 추출
        available_m_cols = [c for c in essential_m_cols if c in df_m_raw.columns]
        df_m = df_m_raw[available_m_cols].copy()

        # 3. 매칭을 위한 임시 키 생성 (이메일 기준)
        df_m['tmp_key'] = df_m['이메일'].astype(str).str.strip().str.lower()
        df_o_raw['tmp_key'] = df_o_raw['주문자 이메일'].astype(str).str.strip().str.lower()

        # 4. 데이터 통합 (주문 내역 전수 유지)
        df_combined = pd.merge(df_o_raw, df_m, on='tmp_key', how='left')

        # 필요 없는 임시 키 및 중복 이메일 컬럼 정리
        if '이메일' in df_combined.columns:
            df_combined = df_combined.drop(columns=['tmp_key', '이메일'])
        else:
            df_combined = df_combined.drop(columns=['tmp_key'])

        # 5. 결과 출력
        st.success(f"✅ 통합 완료: 주문 {len(df_o_raw)}건에 회원 핵심 정보 매칭 완료")
        
        # 필터 기능 (간단히 이름/주문번호 검색용)
        search_term = st.text_input("🔍 검색 (이름 또는 상품명)")
        if search_term:
            df_combined = df_combined[
                df_combined['주문자 이름'].str.contains(search_term, na=False) | 
                df_combined['상품명'].str.contains(search_term, na=False)
            ]

        # 데이터 프레임 표시
        st.dataframe(df_combined.astype(str), use_container_width=True, hide_index=True)

        # 6. 엑셀 다운로드 버튼
        csv = df_combined.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 통합 데이터 다운로드 (CSV)",
            data=csv,
            file_name="LearnIQ_Integrated_Data.csv",
            mime="text/csv",
        )

else:
    st.info("💡 사이드바에서 두 파일을 모두 업로드해 주세요.")
