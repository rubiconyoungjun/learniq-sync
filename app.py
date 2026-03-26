import streamlit as st
import pandas as pd
import json
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# 1. 회원 데이터(A) 정밀 파싱 함수
def parse_member_data(row):
    # 소속기관(그룹) 판별 로직
    group = "미지정(일반)"
    email = ""
    
    # 1순위: 이메일 도메인 분석 (가장 정확함)
    if '주문자 이메일' in row: email = str(row['주문자 이메일'])
    elif 'email' in row: email = str(row['email'])
    
    if 'yonsei.ac.kr' in email: group = "연세대학교"
    elif 'kaist.ac.kr' in email: group = "KAIST"
    elif 'klri.re.kr' in email: group = "한국법제연구원"
    elif 'rubicontech.co.kr' in email: group = "루비콘테크"

    # 2순위: 이름 추출
    name = row.get('주문자 이름') or row.get('name') or row.get('nickname') or "이름없음"
    
    # 3순위: 로그인 횟수 및 가입일
    login_cnt = row.get('로그인 횟수') or row.get('login_cnt') or 0
    reg_date = row.get('주문일') or row.get('reg_date') or "-"
    
    return pd.Series({
        '소속기관': group,
        '이름': name,
        '가입일': reg_date,
        '로그인 횟수': login_cnt,
        '이메일': email
    })

# --- 사이드바 파일 업로드 ---
st.sidebar.header("📁 데이터 업로드 (CSV/XLSX)")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일", type=['csv', 'xlsx'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일", type=['csv', 'xlsx'])

if file_m and file_o:
    with st.spinner('데이터를 통합 분석 중...'):
        df_m_raw = load_data(file_m)
        df_o_raw = load_data(file_o)
        
        # 회원 정보 정리
        df_m = df_m_raw.apply(parse_member_data, axis=1)
        
        # 주문 정보 정리 (이메일 기준 강좌명 콤마 합치기)
        # 샘플 파일의 '주문자 이메일'과 '상품명' 컬럼 사용
        if '주문자 이메일' in df_o_raw.columns and '상품명' in df_o_raw.columns:
            df_o_clean = df_o_raw.groupby('주문자 이메일')['상품명'].apply(
                lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
            ).reset_index()
            df_o_clean.columns = ['이메일', '주문 강좌']
            
            # 데이터 병합
            df_final = pd.merge(df_m, df_o_clean, on='이메일', how='left')
            df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
            
            # --- 결과 화면 ---
            tab1, tab2 = st.tabs(["📋 고객 상세 관리", "📊 기관별 현황"])
            
            with tab1:
                groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                sel_group = st.selectbox("조회할 소속기관 선택", groups)
                
                view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                
                # 요청하신 5대 컬럼 순서대로 출력
                display_cols = ['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']
                st.dataframe(view_df[display_cols], use_container_width=True)
                
                # 엑셀 다운로드 기능
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    view_df[display_cols].to_excel(writer, index=False, sheet_name='Sheet1')
                st.download_button(label="📥 현재 필터 결과 엑셀 다운로드", data=output.getvalue(), file_name=f"{sel_group}_리포트.xlsx")

            with tab2:
                col1, col2 = st.columns(2)
                summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                with col1:
                    st.subheader("기관별 인원 분포")
                    fig = px.pie(summary, values='이름', names='소속기관', hole=.3)
                    st.plotly_chart(fig)
                with col2:
                    st.subheader("기관별 요약 표")
                    st.table(summary.rename(columns={'이름': '인원수'}))
        else:
            st.error("주문 파일에 '주문자 이메일' 또는 '상품명' 컬럼이 없습니다. 파일 양식을 확인해주세요.")
else:
    st.info("사이드바에서 회원 목록과 주문 내역 파일을 업로드해주세요. (CSV, XLSX 모두 지원)")
