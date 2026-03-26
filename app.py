import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="LearnIQ-Sync Dashboard", layout="wide")
st.title("🚀 LearnIQ-Sync B2B 관리 대시보드")

# 사이드바 설정
st.sidebar.header("설정")
api_key = st.sidebar.text_input("아임웹 API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")
api_secret = st.sidebar.text_input("아임웹 Secret Key", value="2c787728a4fe825ad9be8c", type="password")

@st.cache_data
def get_imweb_data(key, secret):
    auth_url = "https://api.imweb.me/v2/auth"
    try:
        auth_res = requests.post(auth_url, data={'key': key, 'secret': secret})
        auth_json = auth_res.json()
        token = auth_json.get('access_token') or auth_json.get('data', {}).get('access_token')
        
        if not token: return None
        
        member_url = "https://api.imweb.me/v2/member/members"
        headers = {'access-token': token}
        member_res = requests.get(member_url, headers=headers)
        return member_res.json().get('data', {}).get('list', [])
    except:
        return None

if st.sidebar.button("데이터 동기화"):
    with st.spinner('아임웹에서 데이터를 가져오는 중...'):
        data = get_imweb_data(api_key, api_secret)
        if data:
            df = pd.DataFrame(data)
            
            # 상단 요약 지표
            col1, col2, col3 = st.columns(3)
            col1.metric("총 회원 수", f"{len(df)}명")
            if 'group_name' in df.columns:
                col2.metric("기관(그룹) 수", f"{len(df['group_name'].unique())}개")
            
            # 기관별 필터
            if 'group_name' in df.columns:
                groups = df['group_name'].unique()
                selected_group = st.selectbox("상세 조회할 기관 선택", groups)
                filtered_df = df[df['group_name'] == selected_group]
                
                st.subheader(f"📊 {selected_group} 회원 명단")
                st.dataframe(filtered_df, use_container_width=True)
                
                st.subheader("📈 기관별 가입 비중")
                st.bar_chart(df['group_name'].value_counts())
            else:
                st.dataframe(df)
        else:
            st.error("데이터를 가져오지 못했습니다. API 키와 설정을 확인하세요.")
