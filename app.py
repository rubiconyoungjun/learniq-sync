import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync 통합 관리 대시보드")

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
    df_m_raw = load_data(file_m)
    
    if df_m_raw is not None:
        # 1. 회원 데이터 컬럼 정리
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        target_cols = ['고유키', '이메일', '회원 그룹', '이름', '이용자 유형', '가입일', '로그인 횟수', '마지막 로그인', '최종 로그인 IP', '구매횟수']
        
        df_m = pd.DataFrame()
        for col in target_cols:
            df_m[col] = df_m_raw[col] if col in df_m_raw.columns else "-"

        # 2. 주문 데이터 처리 (업로드 되었을 경우)
        if file_o:
            df_o_raw = load_data(file_o)
            if df_o_raw is not None:
                df_o_raw.columns = [c.strip() for c in df_o_raw.columns]
                # '주문자 이메일' 또는 '아이디' 컬럼 확인
                o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '아이디'
                
                if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                    # 이메일 기준 중복 제거 및 상품명 합치기
                    df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                    df_o_summary = df_o_raw.groupby(o_email_col)['상품명'].apply(
                        lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                    ).reset_index()
                    df_o_summary.columns = ['이메일', '주문 강좌']
                    
                    # 회원 데이터와 주문 데이터 병합 (이메일 기준)
                    df_m = pd.merge(df_m, df_o_summary, on='이메일', how='left')
                    df_m['주문 강좌'] = df_m['주문 강좌'].fillna("미신청")
                else:
                    st.warning("주문 파일에 '주문자 이메일'이나 '상품명' 컬럼이 없어 연동하지 못했습니다.")
        
        # 3. 🔥 회원 그룹 분할 (콤마 기준 행 복제)
        df_m['회원 그룹'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_display = df_m.explode('회원 그룹')
        df_display['회원 그룹'] = df_display['회원 그룹'].str.strip()

        # 4. 필터링 로직
        all_groups = sorted([g for g in df_display['회원 그룹'].unique() if g not in ["nan", "-", "None"]])
        groups = ["전체"] + all_groups
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 필터링", groups)
        
        filtered_df = df_display if selected_group == "전체" else df_display[df_display['회원 그룹'] == selected_group]

        # 5. 대시보드 출력
        st.subheader(f"📊 {selected_group} 상세 관리 명단")
        # 컬럼 순서 조정 (보기 좋게)
        final_cols = ['회원 그룹', '이름', '이메일'] + [c for c in filtered_df.columns if c not in ['회원 그룹', '이름', '이메일']]
        st.dataframe(filtered_df[final_cols].astype(str), use_container_width=True, hide_index=True)

        # 요약 수치
        c1, c2 = st.columns(2)
        c1.metric("표시된 데이터 수", f"{len(filtered_df)}건")
        if '주문 강좌' in filtered_df.columns:
            active_users = len(filtered_df[filtered_df['주문 강좌'] != "미신청"])
            c2.metric("수강 신청 인원", f"{active_users}명")

else:
    st.info("사이드바에서 회원 목록(필수)과 주문 내역(선택) 파일을 업로드해 주세요.")
