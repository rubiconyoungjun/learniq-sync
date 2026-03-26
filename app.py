import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync 관리 대시보드")

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

if file_m:
    df_raw = load_data(file_m)
    
    if df_raw is not None:
        # 컬럼명 앞뒤 공백 제거
        df_raw.columns = [c.strip() for c in df_raw.columns]
        
        # 요청하신 10가지 항목 매칭 및 추출
        # 엑셀에 해당 컬럼이 없으면 '-'로 표시하도록 안전하게 처리
        display_cols = {
            '고유키': '고유키',
            '이메일': '이메일',
            '회원 그룹': '회원 그룹',
            '이름': '이름',
            '이용자 유형': '이용자 유형',
            '가입일': '가입일',
            '로그인 횟수': '로그인 횟수',
            '마지막 로그인': '마지막 로그인',
            '최종 로그인 IP': '최종 로그인 IP',
            '구매횟수': '구매횟수'
        }
        
        df_display = pd.DataFrame()
        for label, col in display_cols.items():
            if col in df_raw.columns:
                df_display[label] = df_raw[col]
            else:
                df_display[label] = "-" # 컬럼이 없을 경우 대비

        # 기관(회원 그룹)별 필터링
        groups = ["전체"] + sorted(df_display['회원 그룹'].unique().astype(str).tolist())
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 선택", groups)
        
        filtered_df = df_display if selected_group == "전체" else df_display[df_display['회원 그룹'] == selected_group]

        # 대시보드 상단 요약
        col1, col2, col3 = st.columns(3)
        col1.metric("총 회원 수", f"{len(filtered_df)}명")
        col2.metric("선택 그룹", selected_group)
        
        # 메인 테이블 출력
        st.subheader(f"📋 {selected_group} 상세 관리 명단")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # 간단한 통계 차트
        if selected_group == "전체":
            st.subheader("📊 기관별 인원 현황")
            group_counts = df_display['회원 그룹'].value_counts().reset_index()
            group_counts.columns = ['기관명', '인원수']
            fig = px.pie(group_counts, values='인원수', names='기관명', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("왼쪽 사이드바에서 회원 목록 파일을 업로드해 주세요.")
