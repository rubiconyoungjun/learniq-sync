import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Admin", layout="wide")
st.title("🏛️ 기관(그룹)별 수강 현황 리포트")

# --- 데이터 수집 로직 ---
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
st.sidebar.header("⚙️ API 설정")
api_key = st.sidebar.text_input("API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("Secret Key", value="2c787728a4fe825ad9be8c", type="password")

if st.sidebar.button("기관 데이터 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('기관별 매칭 작업을 진행 중입니다...'):
            # 1. 아임웹 데이터 로드
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            # 2. 회원 데이터 정리 (이미지상의 '그룹' 정보 매칭)
            # 아임웹 '그룹' 필드는 보통 group_name에 담깁니다.
            df_m['소속기관'] = df_m['group_name'].fillna('미지정(일반)')
            df_m['이름'] = df_m['name'].fillna(df_m['nickname']).fillna('이름없음')
            if 'reg_date' in df_m.columns:
                df_m['가입일'] = pd.to_datetime(df_m['reg_date'], unit='s').dt.strftime('%Y-%m-%d')
            else:
                df_m['가입일'] = "-"

            # 3. 주문 데이터 정리 (어떤 강좌를 샀는지)
            def parse_order(row):
                items = row.get('items', [])
                prod_name = items[0].get('prod_name') if items else "강좌정보 없음"
                pay = row.get('payment', {})
                return pd.Series({
                    'member_code': row.get('orderer', {}).get('member_code'),
                    '신청강좌': prod_name,
                    '결제금액': pay.get('total_price', 0)
                })
            df_o_clean = df_o.apply(parse_order, axis=1)

            # 4. [핵심] 기관 정보(A) + 주문 정보(B) 매칭
            # 회원 리스트를 기준으로 주문 내역을 붙여서 '수강 안 한 사람'도 나오게 함
            df_final = pd.merge(df_m[['member_code', '소속기관', '이름', '가입일']], 
                                df_o_clean, on='member_code', how='left')
            df_final['신청강좌'] = df_final['신청강좌'].fillna('미신청')

            # --- 대시보드 인터페이스 ---
            # 기관(그룹) 필터
            target_groups = sorted(df_final['소속기관'].unique().tolist())
            selected_group = st.selectbox("🏢 리포트를 뽑을 기관(그룹)을 선택하세요", ["전체"] + target_groups)
            
            view_df = df_final if selected_group == "전체" else df_final[df_final['소속기관'] == selected_group]

            st.divider()

            # 요약 지표
            m1, m2, m3 = st.columns(3)
            m1.metric(f"{selected_group} 총원", f"{len(view_df['member_code'].unique())}명")
            m2.metric("강좌 신청건수", f"{len(view_df[view_df['신청강좌'] != '미신청'])}건")
            m3.metric("누적 매출", f"{view_df['결제금액'].sum():,.0f}원")

            # 상세 데이터 테이블
            st.subheader(f"📋 {selected_group} 상세 수강 현황")
            display_df = view_df[['소속기관', '이름', '가입일', '신청강좌', '결제금액']].sort_values('가입일', ascending=False)
            st.dataframe(display_df, use_container_width=True)

            # 시각화: 인기 강좌
            if not view_df[view_df['신청강좌'] != '미신청'].empty:
                st.subheader(f"📈 {selected_group} 인기 강좌 분포")
                course_data = view_df[view_df['신청강좌'] != '미신청']['신청강좌'].value_counts().reset_index()
                fig = px.bar(course_data, x='count', y='신청강좌', orientation='h', color='신청강좌', text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("데이터를 가져올 수 없습니다. API 키를 확인하세요.")
