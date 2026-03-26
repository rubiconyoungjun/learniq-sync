import streamlit as st
import pandas as pd
import requests
import plotly.express as px # 그래프를 더 예쁘게 그리기 위함

st.set_page_config(page_title="LearnIQ-Sync Pro", layout="wide")
st.title("📊 LearnIQ-Sync 통합 대시보드")

# 사이드바 설정
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("아임웹 API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("아임웹 Secret Key", value="2c787728a4fe825ad9be8c", type="password")

def get_token(key, secret):
    auth_url = "https://api.imweb.me/v2/auth"
    res = requests.post(auth_url, data={'key': key, 'secret': secret}).json()
    return res.get('access_token') or res.get('data', {}).get('access_token')

def get_all_data(url, token):
    all_list = []
    offset = 0
    limit = 100 # 한 번에 100명씩 요청
    
    while True:
        headers = {'access-token': token}
        res = requests.get(f"{url}?offset={offset}&limit={limit}", headers=headers).json()
        items = res.get('data', {}).get('list', [])
        if not items: break
        all_list.extend(items)
        offset += limit
        if len(items) < limit: break # 마지막 페이지면 종료
    return all_list

if st.sidebar.button("데이터 전체 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('아임웹에서 모든 데이터를 불러오는 중...'):
            # 1. 회원 데이터 가져오기
            members = get_all_data("https://api.imweb.me/v2/member/members", token)
            # 2. 주문 데이터 가져오기
            orders = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(members)
            df_o = pd.DataFrame(orders)

            # --- 대시보드 화면 구성 ---
            tab1, tab2 = st.tabs(["👥 회원 관리", "💰 주문 내역"])

            with tab1:
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.metric("총 회원 수", f"{len(df_m)}명")
                    # 기관별 파이 차트
                    if 'group_name' in df_m.columns:
                        fig_member = px.pie(df_m, names='group_name', title='기관별 회원 분포')
                        st.plotly_chart(fig_member)
                
                with col2:
                    st.subheader("회원 상세 목록")
                    st.dataframe(df_m[['member_code', 'nickname', 'group_name', 'reg_date']], use_container_width=True)

            with tab2:
                if not df_o.empty:
                    st.metric("총 주문 건수", f"{len(df_o)}건")
                    # 날짜별 주문 추이 그래프 (간단 버전)
                    st.subheader("주문 목록")
                    st.dataframe(df_o, use_container_width=True)
                else:
                    st.info("가져올 주문 내역이 없습니다.")
    else:
        st.error("인증 실패! API 키를 확인하세요.")
