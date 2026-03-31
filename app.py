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
        rename_o_dict = {
            '주문자 이름': '성명',
            '주문자 이메일': '이메일',
            '주문자 번호': '학번(입력번호)',
            '상품명': '강좌명',
            '주문일': '강좌 신청일'
        }
        
        essential_o_cols = list(rename_o_dict.keys())
        available_o_cols = [c for c in essential_o_cols if c in df_o_raw.columns]
        df_o = df_o_raw[available_o_cols].copy()
        df_o = df_o.rename(columns=rename_o_dict)

        # --- 2. 회원 데이터 필터링 및 용어 변경 ---
        # 구매횟수(KRW)를 강좌 신청 횟수로 변경하기 위한 매핑
        rename_m_dict = {
            '구매횟수(KRW)': '강좌 신청 횟수'
        }
        
        essential_m_cols = [
            '고유키', '이메일', '아이디', '회원 그룹', '이름', 
            '학번 (선택사항)', '이용자 유형', '가입일', '로그인 횟수', 
            '마지막 로그인', '최종 로그인 IP', '구매횟수(KRW)'
        ]
        
        available_m_cols = [c for c in essential_m_cols if c in df_m_raw.columns]
        df_m = df_m_raw[available_m_cols].copy()
        df_m = df_m.rename(columns=rename_m_dict)

        # --- 3. 데이터 매칭 (이메일 기준) ---
        df_o['tmp_key'] = df_o['이메일'].astype(str).str.strip().str.lower()
        df_m['tmp_key'] = df_m['이메일'].astype(str).str.strip().str.lower()

        # 주문 내역 기준 병합
        df_combined = pd.merge(df_o, df_m, on='tmp_key', how='left', suffixes=('', '_회원'))

        # 중복/불필요 컬럼 정리
        cols_to_drop = ['tmp_key', '이메일_회원', '이름'] 
        df_combined = df_combined.drop(columns=[c for c in cols_to_drop if c in df_combined.columns])

        # --- 4. 결과 출력 ---
        st.success(f"✅ 모든 용어 변경 및 데이터 통합 완료 (총 {len(df_o)}건)")
        
        # 검색 기능
        search = st.text_input("🔍 성명 또는 강좌명으로 검색하세요")
        if search:
            df_combined = df_combined[
                df_combined['성명'].str.contains(search, na=False) | 
                df_combined['강좌명'].str.contains(search, na=False)
            ]

        # 최종 데이터 표
        st.dataframe(df_combined.astype(str), use_container_width=True, hide_index=True)

        # CSV 다운로드
        csv = df_combined.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 최종 통합 리포트 다운로드 (CSV)",
            data=csv,
            file_name="LearnIQ_Final_Report_Updated.csv",
            mime="text/csv",
        )
else:
    st.info("💡 사이드바에서 파일을 업로드하면 통합 분석이 시작됩니다.")
