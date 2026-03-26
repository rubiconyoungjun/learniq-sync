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

if file_m:
    df_raw = load_data(file_m)
    
    if df_raw is not None:
        # 1. 컬럼명 정리 및 데이터 추출
        df_raw.columns = [c.strip() for c in df_raw.columns]
        
        target_cols = ['고유키', '이메일', '회원 그룹', '이름', '이용자 유형', '가입일', '로그인 횟수', '마지막 로그인', '최종 로그인 IP', '구매횟수']
        df_display = pd.DataFrame()
        
        for col in target_cols:
            if col in df_raw.columns:
                df_display[col] = df_raw[col]
            else:
                df_display[col] = "-"

        # 2. 🔥 회원 그룹 분리 로직 (중요!)
        # 콤마로 된 문자열을 리스트로 변환 후, explode를 사용하여 행을 복제합니다.
        df_display['회원 그룹'] = df_display['회원 그룹'].astype(str).str.split(',')
        df_display = df_display.explode('회원 그룹')
        # 분리된 그룹명 앞뒤의 공백 제거
        df_display['회원 그룹'] = df_display['회원 그룹'].str.strip()
        
        # 3. 사이드바 필터링 (분리된 그룹 기준으로 정렬)
        all_groups = sorted(df_display['회원 그룹'].unique().tolist())
        if "nan" in all_groups: all_groups.remove("nan")
        if "-" in all_groups: all_groups.remove("-")
        
        groups = ["전체"] + all_groups
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 필터링", groups)
        
        # 필터링 적용
        filtered_df = df_display if selected_group == "전체" else df_display[df_display['회원 그룹'] == selected_group]

        # 4. 결과 출력
        col1, col2 = st.columns([1, 4])
        with col1:
            st.metric("총 데이터 수", f"{len(filtered_df)}건")
        with col2:
            st.info(f"현재 선택된 그룹: **{selected_group}**")
        
        st.subheader("📋 상세 관리 명단")
        # 고유키 등 숫자가 소수점으로 보이지 않게 문자열 처리
        st.dataframe(filtered_df.astype(str), use_container_width=True, hide_index=True)

        # 5. 통계 차트 (전체일 때만 표시)
        if selected_group == "전체":
            st.subheader("📊 기관별 가입 비중")
            group_counts = df_display['회원 그룹'].value_counts().reset_index()
            group_counts.columns = ['기관명', '인원수']
            # 상위 15개 기관만 표시 (너무 많을 경우 대비)
            fig = px.bar(group_counts.head(15), x='기관명', y='인원수', text_auto=True, color='인원수')
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("왼쪽 사이드바에서 회원 목록 파일을 업로드해 주세요.")
