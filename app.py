{\rtf1\ansi\ansicpg949\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import requests\
\
st.set_page_config(page_title="LearnIQ-Sync Dashboard", layout="wide")\
st.title("\uc0\u55357 \u56960  LearnIQ-Sync B2B \u44288 \u47532  \u45824 \u49884 \u48372 \u46300 ")\
\
# \uc0\u49324 \u51060 \u46300 \u48148  \u49444 \u51221  (API \u53412  \u51077 \u47141  - \u45208 \u51473 \u50640  \u48372 \u50504  \u49444 \u51221  \u44032 \u45733 )\
st.sidebar.header("\uc0\u49444 \u51221 ")\
api_key = st.sidebar.text_input("\uc0\u50500 \u51076 \u50937  API Key", value="a2544b90843f56b541bd8b0c62528fa6ed8b2811b0", type="password")\
api_secret = st.sidebar.text_input("\uc0\u50500 \u51076 \u50937  Secret Key", value="2c787728a4fe825ad9be8c", type="password")\
\
@st.cache_data # \uc0\u45936 \u51060 \u53552 \u47484  \u47588 \u48264  \u49352 \u47196  \u44256 \u52840 \u54616 \u51648  \u50506 \u44256  \u52880 \u49884 \u54632 \
def get_imweb_data(key, secret):\
    auth_url = "https://api.imweb.me/v2/auth"\
    auth_res = requests.post(auth_url, data=\{'key': key, 'secret': secret\})\
    token = auth_res.json().get('data', \{\}).get('access_token')\
    \
    if not token: return None\
    \
    member_url = "https://api.imweb.me/v2/member/members"\
    headers = \{'access-token': token\}\
    member_res = requests.get(member_url, headers=headers)\
    return member_res.json().get('data', \{\}).get('list', [])\
\
if st.sidebar.button("\uc0\u45936 \u51060 \u53552  \u46041 \u44592 \u54868 "):\
    data = get_imweb_data(api_key, api_secret)\
    if data:\
        df = pd.DataFrame(data)\
        \
        # \uc0\u49345 \u45800  \u50836 \u50557  \u51648 \u54364 \
        col1, col2, col3 = st.columns(3)\
        col1.metric("\uc0\u52509  \u54924 \u50896  \u49688 ", f"\{len(df)\}\u47749 ")\
        col2.metric("\uc0\u44592 \u44288 (\u44536 \u47353 ) \u49688 ", f"\{len(df['group_name'].unique())\}\u44060 ")\
        \
        # \uc0\u44592 \u44288 \u48324  \u54596 \u53552 \
        selected_group = st.selectbox("\uc0\u49345 \u49464  \u51312 \u54924 \u54624  \u44592 \u44288  \u49440 \u53469 ", df['group_name'].unique())\
        filtered_df = df[df['group_name'] == selected_group]\
        \
        st.subheader(f"\uc0\u55357 \u56522  \{selected_group\} \u54924 \u50896  \u47749 \u45800 ")\
        st.dataframe(filtered_df[['member_code', 'nickname', 'reg_date']], use_container_width=True)\
        \
        # \uc0\u52264 \u53944 \
        st.subheader("\uc0\u55357 \u56520  \u44592 \u44288 \u48324  \u44032 \u51077  \u48708 \u51473 ")\
        group_counts = df['group_name'].value_counts()\
        st.bar_chart(group_counts)\
    else:\
        st.error("\uc0\u45936 \u51060 \u53552 \u47484  \u44032 \u51256 \u50724 \u51648  \u47803 \u54664 \u49845 \u45768 \u45796 . API \u53412 \u47484  \u54869 \u51064 \u54616 \u49464 \u50836 .")}