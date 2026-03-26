import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter

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
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        target_cols = ['고유키', '이메일', '회원 그룹', '이름', '이용자 유형', '가입일', '로그인 횟수', '마지막 로그인', '최종 로그인 IP', '구매횟수']
        
        df_m = pd.DataFrame()
        for col in target_cols:
            df_m[col] = df_m_raw[col] if col in df_m_raw.columns else "-"

        # 주문 데이터 병합
        if file_o:
            df_o_raw = load_data(file_o)
            if df_o_raw is not None:
                df_o_raw.columns = [c.strip() for c in df_o_raw.columns]
                o_email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else '아이디'
                
                if o_email_col in df_o_raw.columns and '상품명' in df_o_raw.columns:
                    df_o_raw[o_email_col] = df_o_raw[o_email_col].astype(str).str.strip()
                    df_o_summary = df_o_raw.groupby(o_email_col)['상품명'].apply(
                        lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                    ).reset_index()
                    df_o_summary.columns = ['이메일', '주문 강좌']
                    df_m = pd.merge(df_m, df_o_summary, on='이메일', how='left')
                    df_m['주문 강좌'] = df_m['주문 강좌'].fillna("미신청")

        # 회원 그룹 분리 (행 복제)
        df_m['회원 그룹'] = df_m['회원 그룹'].astype(str).str.split(',')
        df_display = df_m.explode('회원 그룹')
        df_display['회원 그룹'] = df_display['회원 그룹'].str.strip()

        # 필터링
        all_groups = sorted([g for g in df_display['회원 그룹'].unique() if g not in ["nan", "-", "None"]])
        selected_group = st.sidebar.selectbox("🔍 기관(그룹) 필터링", ["전체"] + all_groups)
        filtered_df = df_display if selected_group == "전체" else df_display[df_display['회원 그룹'] == selected_group]

        # 탭 구성
        tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 강좌 분석 통계"])

        with tab1:
            st.subheader(f"✅ {selected_group} 회원 리스트")
            st.dataframe(filtered_df.astype(str), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader(f"📈 {selected_group} 인기 강좌 TOP 20")
            
            if '주문 강좌' in filtered_df.columns:
                # 1. '미신청' 제외 및 모든 강좌명 수집
                lecture_series = filtered_df[filtered_df['주문 강좌'] != "미신청"]['주문 강좌']
                
                all_lectures = []
                for entry in lecture_series:
                    # 콤마로 구분하여 리스트로 만듦
                    parts = [p.strip() for p in str(entry).split(',') if p.strip()]
                    all_lectures.extend(parts)
                
                if all_lectures:
                    # 2. 빈도수 계산
                    counts = Counter(all_lectures)
                    df_counts = pd.DataFrame(counts.items(), columns=['강좌명', '수강수']).sort_values(by='수강수', ascending=False)
                    
                    # 3. 차트 시각화
                    fig = px.bar(df_counts.head(20), x='수강수', y='강좌명', orientation='h', 
                                 text_auto=True, color='수강수', color_continuous_scale='Blues',
                                 title=f"{selected_group} 그룹 내 최다 수강 강좌")
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 4. 표로 보기
                    with st.expander("전체 강좌 순위 보기"):
                        st.table(df_counts.reset_index(drop=True))
                else:
                    st.warning("분석할 강좌 데이터가 없습니다.")
            else:
                st.info("주문 내역 파일을 먼저 업로드해 주세요.")

else:
    st.info("사이드바에서 파일을 업로드해 주세요.")
