import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import json

st.set_page_config(page_title="LearnIQ-Sync Pro", layout="wide")
st.title("📊 LearnIQ-Sync 통합 관리 시스템")

# 사이드바 설정
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("아임웹 API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("아임웹 Secret Key", value="2c787728a4fe825ad9be8c", type="password")

def get_token(key, secret):
    auth_url = "https://api.imweb.me/v2/auth"
    try:
        res = requests.post(auth_url, data={'key': key, 'secret': secret}).json()
        return res.get('access_token') or res.get('data', {}).get('access_token')
    except: return None

def get_all_data(url, token):
    all_list = []
    offset = 0
    limit = 100 
    while True:
        headers = {'access-token': token}
        try:
            res = requests.get(f"{url}?offset={offset}&limit={limit}", headers=headers).json()
            items = res.get('data', {}).get('list', [])
            if not items: break
            all_list.extend(items)
            offset += limit
            if len(items) < limit: break 
        except: break
    return all_list

if st.sidebar.button("데이터 전체 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('아임웹 데이터를 정밀 분석 중...'):
            # 1. 데이터 가져오기
            members = get_all_data("https://api.imweb.me/v2/member/members", token)
            orders = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(members)
            df_o = pd.DataFrame(orders)

            tab1, tab2 = st.tabs(["👥 전체 고객 목록", "💰 주문 내역 (상세)"])

            with tab1:
                st.metric("총 고객 수", f"{len(df_m)}명")
                # 필터링 없이 모든 컬럼 보여주기
                st.dataframe(df_m, use_container_width=True)
                
                # 파이차트 (그룹 데이터가 있을 경우에만)
                group_col = 'group_name' if 'group_name' in df_m.columns else None
                if group_col and not df_m[group_col].isnull().all():
                    fig = px.pie(df_m, names=group_col, title='기관(그룹)별 분포')
                    st.plotly_chart(fig)

            with tab2:
                if not df_o.empty:
                    # CSV처럼 데이터 풀기 (JSON 파싱)
                    def parse_order(row):
                        # 주문자 정보 추출
                        orderer = row.get('orderer', {})
                        if isinstance(orderer, str): orderer = json.loads(orderer)
                        
                        # 결제 정보 추출
                        payment = row.get('payment', {})
                        if isinstance(payment, str): payment = json.loads(payment)
                        
                        return pd.Series({
                            '주문번호': row.get('order_no'),
                            '주문자': orderer.get('name'),
                            '이메일': orderer.get('email'),
                            '연락처': orderer.get('call'),
                            '결제금액': payment.get('total_price'),
                            '결제수단': payment.get('pay_type'),
                            '주문시간': pd.to_datetime(row.get('order_time'), unit='s').strftime('%Y-%m-%d %H:%M') if row.get('order_time') else '-'
                        })

                    df_o_clean = df_o.apply(parse_order, axis=1)
                    st.metric("총 주문 건수", f"{len(df_o_clean)}건")
                    st.subheader("실시간 주문 리스트")
                    st.dataframe(df_o_clean, use_container_width=True)
                    
                    # 주문 금액 차트
                    fig_order = px.bar(df_o_clean, x='주문시간', y='결제금액', title='일자별 매출 현황')
                    st.plotly_chart(fig_order)
                else:
                    st.info("주문 내역이 없습니다.")
    else:
        st.error("인증 실패!")
