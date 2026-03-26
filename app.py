import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# --- 데이터 수집 함수 (인증/수집 로직은 동일) ---
def get_token(key, secret):
    auth_url = "https://api.imweb.me/v2/auth"
    try:
        res = requests.post(auth_url, data={'key': key, 'secret': secret}).json()
        return res.get('access_token') or res.get('data', {}).get('access_token')
    except: return None

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

if st.sidebar.button("데이터 전체 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('기관별 데이터를 매칭하여 분석 중입니다...'):
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            if not df_m.empty:
                # 1. 회원 정보 전처리 (가입일 변환 포함)
                df_m['기관명'] = df_m['group_name'] if 'group_name' in df_m.columns else '일반회원'
                df_m['수강생명'] = df_m['nickname'] if 'nickname' in df_m.columns else df_m['name']
                
                # 가입일 변환 (Unix 타임스탬프 -> 날짜 문자열)
                if 'reg_date' in df_m.columns:
                    df_m['가입일'] = pd.to_datetime(df_m['reg_date'], unit='s').dt.strftime('%Y-%m-%d')
                else:
                    df_m['가입일'] = "-"

                # 2. 주문 정보 전처리 (구매 강좌 추출)
                def parse_order(row):
                    items = row.get('items', [])
                    prod_name = items[0].get('prod_name') if items else "구매내역 없음"
                    pay = row.get('payment', {})
                    return pd.Series({
                        'member_code': row.get('orderer', {}).get('member_code'),
                        '구매강좌': prod_name,
                        '결제금액': pay.get('total_price', 0)
                    })
                df_o_clean = df_o.apply(parse_order, axis=1)

                # 3. 데이터 결합 (회원 리스트에 주문 정보를 붙임)
                # how='left'를 써서 구매 안 한 회원도 리스트에 나오게 함
                df_final = pd.merge(df_m[['member_code', '기관명', '수강생명', '가입일']], 
                                    df_o_clean, on='member_code', how='left')
                
                # 구매내역 없는 사람 빈칸 처리
                df_final['구매강좌'] = df_final['구매강좌'].fillna('미구매')
                df_final['결제금액'] = df_final['결제금액'].fillna(0)

                # --- 화면 출력 ---
                groups = sorted(df_final['기관명'].unique().tolist())
                selected_group = st.selectbox("📊 조회할 기관(그룹) 선택", ["전체"] + groups)
                
                target_df = df_final if selected_group == "전체" else df_final[df_final['기관명'] == selected_group]

                st.divider()
                
                # 지표 요약
                c1, c2, c3 = st.columns(3)
                c1.metric("해당 기관 회원수", f"{len(target_df['member_code'].unique())}명")
                c2.metric("강좌 구매건수", f"{len(target_df[target_df['구매강좌'] != '미구매'])}건")
                c3.metric("누적 매출액", f"{target_df['결제금액'].sum():,.0f}원")

                # 상세 표 (가장 중요한 부분)
                st.subheader(f"📋 {selected_group} 상세 관리 명단")
                # 컬럼 순서 조정: 가입일과 강좌명을 전진 배치
                display_cols = ['기관명', '수강생명', '가입일', '구매강좌', '결제금액']
                st.dataframe(target_df[display_cols].sort_values('가입일', ascending=False), use_container_width=True)

                # 시각화
                if selected_group == "전체":
                    st.subheader("🏢 기관별 회원 분포")
                    fig = px.pie(df_final, names='기관명')
                    st.plotly_chart(fig)
                else:
                    st.subheader(f"📖 {selected_group} 인기 강좌")
                    course_counts = target_df[target_df['구매강좌'] != '미구매']['구매강좌'].value_counts().reset_index()
                    fig = px.bar(course_counts, x='count', y='구매강좌', orientation='h', color='구매강좌')
                    st.plotly_chart(fig)
    else:
        st.error("API 연결 실패!")
