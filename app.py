import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 수강 현황 대시보드")

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
        try:
            res = requests.get(f"{url}?offset={offset}&limit={limit}", headers=headers).json()
            items = res.get('data', {}).get('list', [])
            if not items: break
            all_list.extend(items)
            offset += limit
            if len(items) < limit: break
        except: break
    return all_list

# 사이드바 설정
st.sidebar.header("⚙️ 관리자 설정")
api_key = st.sidebar.text_input("API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("Secret Key", value="2c787728a4fe825ad9be8c", type="password")

if st.sidebar.button("데이터 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('데이터를 정밀 분석 중...'):
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            if not df_m.empty and not df_o.empty:
                # 1. 회원 데이터 정리 (이름 유연하게 찾기)
                # group_name이 없으면 '일반'으로, nickname이 없으면 name으로 대체
                df_m['기관명'] = df_m['group_name'] if 'group_name' in df_m.columns else (df_m['group'] if 'group' in df_m.columns else '일반회원')
                df_m['수강생'] = df_m['nickname'] if 'nickname' in df_m.columns else (df_m['name'] if 'name' in df_m.columns else '이름없음')
                
                # 2. 주문 데이터 정리
                def extract_order_info(row):
                    orderer = row.get('orderer', {})
                    payment = row.get('payment', {})
                    items = row.get('items', [])
                    prod_name = items[0].get('prod_name') if items else "미확인 강좌"
                    return pd.Series({
                        'member_code': orderer.get('member_code'),
                        '강좌명': prod_name,
                        '결제금액': payment.get('total_price', 0)
                    })
                
                df_o_clean = df_o.apply(extract_order_info, axis=1)

                # 3. 매칭 (Merge) - 안전하게 정리된 컬럼만 사용
                df_final = pd.merge(df_o_clean, df_m[['member_code', '기관명', '수강생']], on='member_code', how='left')
                df_final['기관명'] = df_final['기관명'].fillna('미지정 기관')

                # --- 대시보드 화면 ---
                all_groups = sorted(df_final['기관명'].unique().tolist())
                selected_group = st.selectbox("📊 분석할 기관(그룹)을 선택하세요", ["전체보기"] + all_groups)
                
                target_df = df_final if selected_group == "전체보기" else df_final[df_final['기관명'] == selected_group]

                st.divider()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("총 수강 인원", f"{len(target_df['member_code'].unique())}명")
                c2.metric("총 수강 신청", f"{len(target_df)}건")
                c3.metric("누적 매출액", f"{target_df['결제금액'].sum():,.0f}원")

                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader(f"🏆 {selected_group} 인기 강좌")
                    top_courses = target_df['강좌명'].value_counts().reset_index()
                    fig = px.bar(top_courses, x='count', y='강좌명', orientation='h', color='강좌명', text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)

                with col_right:
                    st.subheader("📋 상세 수강 내역")
                    st.dataframe(target_df[['수강생', '강좌명', '결제금액', '기관명']], use_container_width=True)
            else:
                st.warning("회원 또는 주문 데이터가 부족합니다.")
    else:
        st.error("API 토큰을 가져오지 못했습니다.")
