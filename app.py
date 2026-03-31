import streamlit as st
import pandas as pd

st.set_page_config(page_title="LearnIQ Core Dashboard", layout="wide")
st.title("🎯 LearnIQ 통합 수강 관리 시스템")

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
file_m = st.sidebar.file_uploader("1. 회원 목록 파일", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 컬럼명 앞뒤 공백 제거
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # --- 1. 주문 데이터 필터링 및 용어 변경 ---
        # 원본 컬럼명 -> 변경할 컬럼명 매핑
        rename_dict = {
            '주문자 이름': '성명',
            '주문자 이메일': '이메일',
            '주문자 번호': '학번(입력번호)',
            '상품명': '강좌명',
            '주문일': '강좌 신청일'
        }
        
        # 필요한 항목만 추출
        essential_o_cols = list(rename_dict.keys())
        available_o_cols = [c for c in essential_o_cols if c in df_o_raw.columns]
        df_o = df_o_raw[available_o_cols].copy()
        
        # 용어 변경 적용
        df_o = df_o.rename(columns=rename_dict)

        # --- 2. 회원 데이터 필터링 (12개 항목) ---
        essential_m_cols = [
            '고유키', '이메일', '아이디', '회원 그룹', '이름', 
            '학번 (선택사항)', '이용자 유형', '가입일', '로그인 횟수', 
            '마지막 로그인', '최종 로그인 IP', '구매횟수(KRW)'
        ]
        available_m_cols = [c for c in essential_m_cols if c in df_m_raw.columns]
        df_m = df_m_raw[available_m_cols].copy()

        # --- 3. 데이터 매칭 (이메일 기준) ---
        # 매칭용 임시 키 생성 (소문자화)
        df_o['tmp_key'] = df_o['이메일'].astype(str).str.strip().str.lower()
        df_m['tmp_key'] = df_m['이메일'].astype(str).str.strip().str.lower()

        # 주문 내역을 기준으로 회원 정보를 병합
        df_combined = pd.merge(df_o, df_m, on='tmp_key', how='left', suffixes=('', '_회원'))

        # 중복되거나 불필요한 컬럼 정리
        cols_to_drop = ['tmp_key', '이메일_회원', '이름'] # 주문 정보의 '성명'과 '이메일'을 유지
        df_combined = df_combined.drop(columns=[c for c in cols_to_drop if c in df_combined.columns])

        # --- 4. 결과 출력 ---
        st.success(f"✅ 데이터 통합 및 용어 변경 완료 (총 {len(df_o)}건)")
        
        # 검색 및 필터 인터페이스
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search = st.text_input("🔍 성명 또는 강좌명 검색")
        
        if search:
            df_combined = df_combined[
                df_combined['성명'].str.contains(search, na=False) | 
                df_combined['강좌명'].str.contains(search, na=False)
            ]

        # 데이터 프레임 표시
        st.dataframe(df_combined.astype(str), use_container_width=True, hide_index=True)

        # CSV 다운로드
        csv = df_combined.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 정리된 데이터 다운로드 (CSV)",
            data=csv,
            file_name="LearnIQ_Final_Report.csv",
            mime="text/csv",
        )
else:
    st.info("💡 사이드바에서 회원 목록과 주문 내역 파일을 업로드해 주세요.")
