import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 리포트")

# --- 데이터 수집 함수 ---
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

if st.sidebar.button("데이터 동기화 🔄"):
    token = get_token(api_key, api_secret)
    if token:
        with st.spinner('실시간 데이터를 분석 중입니다...'):
            m_list = get_all_data("https://api.imweb.me/v2/member/members", token)
            o_list = get_all_data("https://api.imweb.me/v2/shop/orders", token)
            
            df_m_raw = pd.DataFrame(m_list)
            df_o_raw = pd.DataFrame(o_list)

            if not df_m_raw.empty:
                # 1. 회원 정보 안전하게 정리 (KeyError 방지)
                def clean_m(row):
                    # 소속기관 찾기
                    group = "미지정(일반)"
                    if 'group_name' in row and pd.notnull(row['group_name']):
                        group = row['group_name']
                    elif 'groups' in row and isinstance(row['groups'], list) and len(row['groups']) > 0:
                        group = row['groups'][0].get('name', '미지정(일반)')
                    
                    return pd.Series({
                        'member_code': str(row.get('member_code', '')),
                        '소속기관': group,
                        '이름': row.get('name') or row.get('nickname') or "이름없음",
                        '가입일': pd.to_datetime(row.get('reg_date'), unit='s').strftime('%Y-%m-%d') if row.get('reg_date') else "-",
                        '로그인 횟수': row.get('login_cnt', 0)
                    })
                
                df_m = df_m_raw.apply(clean_m, axis=1)

                # 2. 주문 정보 정리 (강좌명 콤마 합산)
                order_map = {}
                if not df_o_raw.empty:
                    for _, row in df_o_raw.iterrows():
                        m_code = str(row.get('orderer', {}).get('member_code', ''))
                        if not m_code: continue
                        
                        items = row.get('items', [])
                        prods = [i.get('prod_name') for i in items if i.get('prod_name')]
                        
                        if m_code not in order_map: order_map[m_code] = []
                        order_map[m_code].extend(prods)
                
                df_o = pd.DataFrame([{'member_code': k, '주문 강좌': ", ".join(list(set(v)))} for k, v in order_map.items()])

                # 3. 데이터 합치기
                if not df_o.empty:
                    df_final = pd.merge(df_m, df_o, on='member_code', how='left')
                else:
                    df_final = df_m
                    df_final['주문 강좌'] = "미신청"
                
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")

                # --- 결과 출력 ---
                tab1, tab2 = st.tabs(["📋 상세 관리", "📊 기관 통계"])
                
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel = st.selectbox("기관 선택", groups)
                    view = df_final if sel == "전체" else df_final[df_final['소속기관'] == sel]
                    st.dataframe(view[['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']], use_container_width=True)
                
                with tab2:
                    summary = df_final.groupby('소속기관')['member_code'].count().reset_index()
                    st.bar_chart(summary.set_index('소속기관'))
            else:
                st.warning("데이터를 가져오지 못했습니다.")
    else:
        st.error("API 인증에 실패했습니다.")
