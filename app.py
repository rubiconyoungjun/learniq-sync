import streamlit as st
import pandas as pd

st.set_page_config(page_title="LearnIQ Data Master", layout="wide")
st.title("통합 데이터 전수 조사 모드")

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
    df_m = load_data(file_m)
    df_o = load_data(file_o)
    
    if df_m is not None and df_o is not None:
        # 컬럼명 정리
        df_m.columns = [c.strip() for c in df_m.columns]
        df_o.columns = [c.strip() for c in df_o.columns]

        # 매칭을 위한 임시 키 생성 (소문자/공백제거)
        df_m['tmp_key'] = df_m['이메일'].astype(str).str.strip().str.lower()
        df_o['tmp_key'] = df_o['주문자 이메일'].astype(str).str.strip().str.lower()

        # [데이터 통합] 주문 내역을 왼쪽(Left)에 두고 회원 정보를 모두 붙임
        # 주문 내역의 모든 컬럼 + 회원 목록의 모든 컬럼이 합쳐집니다.
        df_combined = pd.merge(df_o, df_m, on='tmp_key', how='left')

        # 필요 없는 임시 키 삭제
        df_combined = df_combined.drop(columns=['tmp_key'])

        # 메인 화면 지표
        st.info(f"✅ 통합 완료: 주문 내역 {len(df_o)}건에 대해 회원 정보를 매칭했습니다.")
        
        # 전체 데이터 표시
        st.subheader("📊 전체 통합 데이터 (전수 표시)")
        st.write("아래 표에는 두 파일의 모든 컬럼이 합쳐져 있습니다. 오른쪽으로 스크롤하여 확인하세요.")
        
        # 모든 데이터를 문자열로 변환하여 안전하게 표시
        st.dataframe(df_combined.astype(str), use_container_width=True)

        # 엑셀 다운로드 기능 (참고용)
        csv = df_combined.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 통합 데이터 다운로드 (CSV)",
            data=csv,
            file_name="combined_data_all.csv",
            mime="text/csv",
        )

else:
    st.info("💡 사이드바에서 두 파일을 모두 업로드하면 통합 표가 생성됩니다.")
