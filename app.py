import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Pro", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# --- API 수집 함수 ---
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

# --- 사이드바 ---
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input("API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("Secret Key", value="2c787728a4fe825ad9be8c", type="password")

if st.sidebar.button("데이터 동기화 시작 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('데이터를 매칭 중입니다...'):
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m = pd.DataFrame(m_list)
            df_o = pd.DataFrame(o_list)

            if not df_m.empty:
                # [데이터 디버깅용 - 기관명이 안 나올 때 확인용]
                # st.write(m_list[0]) # 첫 번째 회원 데이터 구조 출력 (필요시 주석 해제)

                # 1. 회원 정보 정밀 파싱
                def parse_member(row):
                    # 소속기관(그룹) 찾기 로직 강화
                    group = "미지정(일반)"
                    if 'group_name' in row and pd.notnull(row['group_name']):
                        group = row['group_name']
                    elif 'groups' in row and isinstance(row['groups'], list) and len(row['groups']) > 0:
                        group = row['groups'][0].get('name', '미지정(일반)')
                    
                    return pd.Series({
                        'member_code': str(row.get('member_code')),
                        '소속기관': group,
                        '이름': row.get('name') or row.get('nickname') or "이름없음",
                        '가입일': pd.to_datetime(row.get('reg_date'), unit='s').strftime('%Y-%m-%d') if row.get('reg_date') else "-",
                        '로그인 횟수': row.get('login_cnt', 0)
                    })

                df_m_clean = df_m.apply(parse_member, axis=1)

                # 2. 주문 정보 정리 (강좌명을 회원별로 콤마 합산)
                order_map = {}
                if not df_o.empty:
                    for _, row in df_o.iterrows():
                        m_code = str(row.get('orderer', {}).get('member_code'))
                        items = row.get('items', [])
                        prod_names = [it.get('prod_name') for it in items if it.get('prod_name')]
                        
                        if m_code not in order_map:
                            order_map[m_code] = []
                        order_map[m_code].extend(prod_names)

                # 리스트를 콤마로 합치기
                order_data = []
                for m_code, prods in order_map.items():
                    order_data.append({
                        'member_code': m_code,
                        '주문 강좌': ", ".join(list(set(prods))) # 중복 제거 후 합침
                    })
                df_o_clean = pd.DataFrame(order_data)

                # 3. 데이터 합치기
                df_final = pd.merge(df_m_clean, df_o_clean, on='member_code', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")

                # --- 화면 출력 (탭 구성) ---
                tab1, tab2 = st.tabs(["📋 고객 상세 관리", "📊 기관별 통계"])

                with tab1:
                    # 기관 필터
                    groups = sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("조회할 기관 선택", ["전체"] + groups)
                    
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    # 원하는 5개 컬럼 출력
                    st.dataframe(view_df[['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']], use_container_width=True)

                with tab2:
                    st.subheader("🏢 기관별 수강 현황 요약")
                    summary = df_final.groupby('소속기관').agg({
                        'member_code': 'count',
                        '로그인 횟수': 'sum'
                    }).rename(columns={'member_code': '총 인원'}).reset_index()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("기관별 인원수")
                        st.bar_chart(summary.set_index('소속기관')['총 인원'])
                    with col2:
                        st.write("기관별 상세 지표")
                        st.table(summary)
            else:
                st.warning("회원 데이터가 없습니다.")
    else:
        st.error("API 인증 실패!")
