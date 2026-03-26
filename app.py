import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
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
st.sidebar.header("⚙️ API 설정")
api_key = st.sidebar.text_input("API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("Secret Key", value="2c787728a4fe825ad9be8c", type="password")

if st.sidebar.button("데이터 동기화 및 매칭 시작 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('기관 정보를 정밀 분석 중입니다...'):
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            if not df_m.empty:
                # 1. [핵심 수정] 소속기관(그룹)을 찾는 정밀 로직
                def find_group_name(row):
                    # 1순위: group_name 필드 확인
                    if 'group_name' in row and pd.notnull(row['group_name']):
                        return row['group_name']
                    # 2순위: groups 리스트 내의 name 확인 (아임웹의 복합 구조 대응)
                    if 'groups' in row and isinstance(row['groups'], list) and len(row['groups']) > 0:
                        return row['groups'][0].get('name', '미지정(일반)')
                    # 3순위: group 필드 확인
                    if 'group' in row and pd.notnull(row['group']):
                        return row['group']
                    return '미지정(일반)'

                df_m['소속기관'] = df_m.apply(find_group_name, axis=1)
                df_m['이름'] = df_m['name'].fillna(df_m['nickname']).fillna('이름없음')
                
                if 'reg_date' in df_m.columns:
                    df_m['가입일'] = pd.to_datetime(df_m['reg_date'], unit='s').dt.strftime('%Y-%m-%d')
                else:
                    df_m['가입일'] = "-"

                # 2. 주문 정보 정리 (강좌명 추출)
                order_items = []
                if not df_o.empty:
                    for _, row in df_o.iterrows():
                        m_code = row.get('orderer', {}).get('member_code')
                        items = row.get('items', [])
                        pay = row.get('payment', {})
                        if items:
                            for item in items:
                                order_items.append({
                                    'member_code': m_code,
                                    '신청강좌': item.get('prod_name', '정보없음'),
                                    '결제금액': pay.get('total_price', 0)
                                })
                    df_o_clean = pd.DataFrame(order_items)
                else:
                    df_o_clean = pd.DataFrame(columns=['member_code', '신청강좌', '결제금액'])

                # 3. 매칭 및 최종 결과 생성
                df_final = pd.merge(df_m[['member_code', '소속기관', '이름', '가입일']], 
                                    df_o_clean, on='member_code', how='left')
                df_final['신청강좌'] = df_final['신청강좌'].fillna('미신청')
                df_final['결제금액'] = df_final['결제금액'].fillna(0)

                # --- UI 출력 ---
                target_groups = sorted(df_final['소속기관'].unique().tolist())
                selected_group = st.selectbox("🏢 리포트를 확인할 기관을 선택하세요", ["전체"] + target_groups)
                
                view_df = df_final if selected_group == "전체" else df_final[df_final['소속기관'] == selected_group]

                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("총 인원", f"{len(view_df['member_code'].unique())}명")
                c2.metric("수강 신청", f"{len(view_df[view_df['신청강좌'] != '미신청'])}건")
                c3.metric("누적 매출", f"{view_df['결제금액'].sum():,.0f}원")

                st.subheader(f"📋 {selected_group} 상세 내역")
                st.dataframe(view_df[['소속기관', '이름', '가입일', '신청강좌', '결제금액']].sort_values('가입일', ascending=False), use_container_width=True)

                if selected_group != "전체" and not view_df[view_df['신청강좌'] != '미신청'].empty:
                    st.subheader(f"📊 {selected_group} 인기 강좌")
                    course_chart = view_df[view_df['신청강좌'] != '미신청']['신청강좌'].value_counts().reset_index()
                    fig = px.bar(course_chart, x='count', y='신청강좌', orientation='h', color='신청강좌', text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("데이터 로딩 중...")
    else:
        st.error("API 인증 실패!")
