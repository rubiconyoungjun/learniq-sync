import streamlit as st
import pandas as pd

st.set_page_config(page_title="LearnIQ Data Master", layout="wide")
st.title("🎯 LearnIQ 주문-회원 데이터 통합 관리")

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
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 (Master: 기본_양식...)", type=['csv', 'xlsx'])

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        # 0. 컬럼명 공백 정리
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # --- 1. Master(주문 내역) 데이터 필수 항목 추출 및 용어 변경 ---
        # 사용자가 요청한 5개 핵심 주문 컬럼
        rename_o_dict = {
            '주문자 이름': '성명',
            '주문자 이메일': '이메일',
            '주문자 번호': '학번(입력번호)',
            '상품명': '강좌명',
            '주문일': '강좌 신청일'
        }
        df_master = df_o_raw[list(rename_o_dict.keys())].copy().rename(columns=rename_o_dict)

        # --- 2. 회원 목록 정제: 'AI-' 시작 텍스트 삭제 ---
        def clean_ai_text(group_str):
            if pd.isna(group_str) or str(group_str).strip() == "":
                return "-"
            # 콤마로 분리 -> AI- 제외 -> 다시 합치기
            parts = [p.strip() for p in str(group_str).split(',')]
            cleaned = [p for p in parts if not p.upper().startswith('AI-')]
            return ", ".join(cleaned) if cleaned else "-"

        df_m_cleaned = df_m_raw.copy()
        df_m_cleaned['회원 그룹'] = df_m_cleaned['회원 그룹'].apply(clean_ai_text)
        
        # 회원 목록에서 가져올 추가 정보 리스트 (용어 변경 포함)
        m_cols_to_fetch = [
            '이메일', '고유키', '아이디', '회원 그룹', '이용자 유형', 
            '가입일', '로그인 횟수', '마지막 로그인', '구매횟수(KRW)'
        ]
        available_m = [c for c in m_cols_to_fetch if c in df_m_cleaned.columns]
        df_m_subset = df_m_cleaned[available_m].copy()
        df_m_subset = df_m_subset.rename(columns={'구매횟수(KRW)': '강좌 신청 횟수'})

        # --- 3. 데이터 연결 (Key: 이메일) ---
        # 매칭용 소문자 키 생성 (데이터 정규화)
        df_master['match_key'] = df_master['이메일'].astype(str).str.strip().str.lower()
        df_m_subset['match_key'] = df_m_subset['이메일'].astype(str).str.strip().str.lower()

        # Master(주문)를 기준으로 회원 정보를 결합 (Left Join)
        df_final = pd.merge(
            df_master, 
            df_m_subset.drop(columns=['이메일']), # 중복 컬럼 방지
            on='match_key', 
            how='left'
        )

        # --- 4. 최종 데이터 정리 ---
        # 매칭되지 않은 데이터(nan)를 '-'로 채우기
        df_final = df_final.drop(columns=['match_key']).fillna("-")

        # --- 5. 화면 표시 ---
        st.success(f"✅ 통합 완료: 주문 내역(Master) {len(df_master)}건 기준 매칭 성공")
        
        # 검색 필터
        search = st.text_input("🔍 성명 또는 강좌명으로 검색")
        if search:
            df_final = df_final[
                df_final['성명'].str.contains(search, na=False) | 
                df_final['강좌명'].str.contains(search, na=False)
            ]

        st.subheader("📋 통합 수강 관리 리스트")
        st.dataframe(df_final.astype(str), use_container_width=True, hide_index=True)

        # 다운로드 버튼
        csv = df_final.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 최종 통합 데이터 다운로드 (CSV)",
            data=csv,
            file_name="LearnIQ_Final_Report.csv",
            mime="text/csv"
        )
else:
    st.info("💡 사이드바에서 주문 내역(Master)과 회원 목록 파일을 업로드해 주세요.")
