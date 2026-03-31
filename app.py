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

        # --- 1. 주문 데이터 전처리 (용어 변경) ---
        rename_o_dict = {
            '주문자 이름': '성명',
            '주문자 이메일': '이메일',
            '주문자 번호': '학번(입력번호)',
            '상품명': '강좌명',
            '주문일': '강좌 신청일'
        }
        df_o = df_o_raw[list(rename_o_dict.keys())].copy().rename(columns=rename_o_dict)

        # --- 2. 회원 데이터 전처리 (AI- 삭제 및 nan 방지) ---
        df_m = df_m_raw.copy()
        
        # [회원 그룹]에서 AI-로 시작하는 단어들만 골라 삭제하는 함수
        def clean_member_group(group_str):
            if pd.isna(group_str) or str(group_str).strip() == "":
                return "(소속없음)"
            # 콤마로 분리하여 각 항목 검사
            parts = [p.strip() for p in str(group_str).split(',')]
            # AI-로 시작하지 않는 항목만 남김
            cleaned_parts = [p for p in parts if not p.upper().startswith('AI-')]
            # 남은 항목이 있으면 합치고, 없으면 소속없음 표시
            return ", ".join(cleaned_parts) if cleaned_parts else "(기관명 미입력)"

        df_m['회원 그룹'] = df_m['회원 그룹'].apply(clean_member_group)

        # 표시할 필수 컬럼 선택
        essential_m_cols = [
            '고유키', '이메일', '아이디', '회원 그룹', '이름', 
            '학번 (선택사항)', '이용자 유형', '가입일', '로그인 횟수', 
            '마지막 로그인', '최종 로그인 IP', '구매횟수(KRW)'
        ]
        available_m_cols = [c for c in essential_m_cols if c in df_m.columns]
        df_m = df_m[available_m_cols].copy()
        df_m = df_m.rename(columns={'구매횟수(KRW)': '강좌 신청 횟수'})

        # --- 3. 데이터 병합 (Left Join) ---
        df_o['tmp_key'] = df_o['이메일'].astype(str).str.strip().str.lower()
        df_m['tmp_key'] = df_m['이메일'].astype(str).str.strip().str.lower()

        df_combined = pd.merge(df_o, df_m, on='tmp_key', how='left', suffixes=('', '_회원'))

        # --- 4. 최종 nan 처리 (모든 결측치를 "-"로 변경) ---
        df_combined = df_combined.fillna("-")
        
        # 불필요 컬럼 삭제
        cols_to_drop = ['tmp_key', '이메일_회원', '이름']
        df_combined = df_combined.drop(columns=[c for c in cols_to_drop if c in df_combined.columns])

        # --- 5. 결과 출력 ---
        st.success(f"✅ 데이터 매칭 완료 (총 {len(df_o)}건)")
        
        # 검색 필터
        search = st.text_input("🔍 성명 또는 강좌명 검색")
        if search:
            df_combined = df_combined[
                df_combined['성명'].str.contains(search, na=False) | 
                df_combined['강좌명'].str.contains(search, na=False)
            ]

        st.dataframe(df_combined.astype(str), use_container_width=True, hide_index=True)

        # CSV 다운로드
        csv = df_combined.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(label="📥 최종 리포트 다운로드", data=csv, file_name="LearnIQ_Final.csv")
else:
    st.info("💡 사이드바에서 파일을 업로드해 주세요.")
