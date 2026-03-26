import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ 기관별 수강 현황 리포트 (통합판)")

# 1. 회원 데이터 파싱 함수
def parse_member_data(row):
    try:
        # JSON 형식의 orderer 컬럼 파싱 (CSV 샘플 기준)
        orderer = json.loads(row['orderer']) if isinstance(row['orderer'], str) else row['orderer']
        email = orderer.get('email', '')
        
        # 이메일 도메인으로 기관명 자동 분류 (샘플 데이터 기반)
        if 'yonsei.ac.kr' in email: group = "연세대학교"
        elif 'kaist.ac.kr' in email: group = "KAIST"
        elif 'klri.re.kr' in email: group = "한국법제연구원"
        else: group = "기타/일반"
        
        return pd.Series({
            'member_code': orderer.get('member_code'),
            '이름': orderer.get('name', '이름없음'),
            '소속기관': group,
            '이메일': email
        })
    except:
        return pd.Series({'member_code': None, '이름': '데이터오류', '소속기관': '분류불가', '이메일': ''})

# --- 데이터 로드 및 처리 ---
# 실전에서는 API 호출 결과를 사용하되, 여기서는 보내주신 CSV 구조에 맞게 로직을 짰습니다.
def process_data(df_m_raw, df_o_raw):
    # 회원 정보 정리
    df_m = df_m_raw.apply(parse_member_data, axis=1).dropna(subset=['member_code'])
    
    # 주문 정보 정리 (강좌명 추출 및 중복 제거 후 합치기)
    # df_o_raw에는 '주문자 이메일'과 '상품명'이 있음
    df_o_clean = df_o_raw.groupby('주문자 이메일')['상품명'].apply(lambda x: ", ".join(list(set(x)))).reset_index()
    df_o_clean.columns = ['이메일', '주문 강좌']
    
    # 두 데이터 매칭 (이메일 기준이 가장 확실함)
    df_final = pd.merge(df_m, df_o_clean, on='이메일', how='left')
    df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
    
    return df_final

# --- UI 부분 ---
uploaded_m = st.sidebar.file_uploader("회원 CSV 업로드", type="csv")
uploaded_o = st.sidebar.file_uploader("주문 CSV 업로드", type="csv")

if uploaded_m and uploaded_o:
    df_m_raw = pd.read_csv(uploaded_m)
    df_o_raw = pd.read_csv(uploaded_o)
    
    df_final = process_data(df_m_raw, df_o_raw)
    
    # 탭 구성
    tab1, tab2 = st.tabs(["📋 상세 현황", "📊 기관별 통계"])
    
    with tab1:
        selected_group = st.selectbox("기관 선택", ["전체"] + sorted(df_final['소속기관'].unique().tolist()))
        view_df = df_final if selected_group == "전체" else df_final[df_final['소속기관'] == selected_group]
        
        # 원하는 컬럼 순서로 출력
        st.dataframe(view_df[['소속기관', '이름', '이메일', '주문 강좌']], use_container_width=True)
        
    with tab2:
        st.subheader("기관별 수강 신청 인원")
        summary = df_final.groupby('소속기관')['이름'].count().reset_index()
        summary.columns = ['소속기관', '인원수']
        st.bar_chart(summary.set_index('소속기관'))
        st.table(summary)
else:
    st.info("왼쪽 사이드바에서 두 개의 CSV 파일을 모두 업로드해주세요.")
