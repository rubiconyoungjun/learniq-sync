import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 수강 현황 대시보드")

# 1. API 인증 및 데이터 수집 함수 (기존과 동일)
def get_token(key, secret):
    auth_url = "https://api.imweb.me/v2/auth"
    res = requests.post(auth_url, data={'key': key, 'secret': secret}).json()
    return res.get('access_token') or res.get('data', {}).get('access_token')

def get_all_data(url, token):
    all_list = []
    offset, limit = 0, 100
    while True:
        headers = {'access-token': token}
        res = requests.get(f"{url}?offset={offset}&limit={limit}", headers=headers).json()
        items = res.get('data', {}).get('list', [])
        if not items: break
        all_list.extend(items)
        offset += limit
        if len(items) < limit: break
    return all_list

# 사이드바 설정
st.sidebar.header("⚙️ 관리자 설정")
api_key = st.sidebar.text_input("API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("Secret Key", value="2c787728a4fe825ad9be8c", type="password")

if st.sidebar.button("데이터 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('데이터를 매칭 중입니다...'):
            # 데이터 가져오기
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            # [핵심] 주문 데이터에서 member_code 추출하여 정리
            def extract_order_info(row):
                orderer = row.get('orderer', {})
                payment = row.get('payment', {})
                # 품목 정보 (강좌명) 추출 - 첫 번째 품목 기준
                items = row.get('items', [])
                prod_name = items[0].get('prod_name') if items else "알 수 없는 강좌"
                
                return pd.Series({
                    'member_code': orderer.get('member_code'),
                    '강좌명': prod_name,
                    '결제금액': payment.get('total_price', 0)
                })
            
            df_o_clean = df_o.apply(extract_order_info, axis=1)

            # [매칭] 회원 정보(A)와 주문 정보(B)를 member_code 기준으로 합치기
            # 회원 정보에서 그룹명(기관명)만 가져와서 주문에 붙임
            df_final = pd.merge(df_o_clean, df_m[['member_code', 'group_name', 'nickname']], on='member_code', how='left')

            # --- 대시보드 화면 ---
            # 1. 기관 선택 필터
            all_groups = df_final['group_name'].unique().tolist()
            selected_group = st.selectbox("📊 분석할 기관(그룹)을 선택하세요", ["전체"] + all_groups)
            
            target_df = df_final if selected_group == "전체" else df_final[df_final['group_name'] == selected_group]

            # 2. 주요 지표
            c1, c2, c3 = st.columns(3)
            c1.metric("총 수강 인원", f"{len(target_df['member_code'].unique())}명")
            c2.metric("총 수강 신청 건수", f"{len(target_df)}건")
            c3.metric("누적 매출", f"{target_df['결제금액'].sum():,.0f}원")

            st.divider()

            # 3. 시각화 (인기 강좌 순위)
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader(f"🏆 {selected_group} 인기 강좌 TOP 5")
                top_courses = target_df['강좌명'].value_counts().head(5).reset_index()
                fig = px.bar(top_courses, x='count', y='강좌명', orientation='h', color='강좌명')
                st.plotly_chart(fig, use_container_width=True)

            with col_right:
                st.subheader("📋 수강생별 상세 내역")
                st.dataframe(target_df[['nickname', '강좌명', '결제금액', 'group_name']], use_container_width=True)

    else:
        st.error("인증 실패!")
