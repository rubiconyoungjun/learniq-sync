import streamlit as st
import pandas as pd

# ... (기존 load_data 함수 생략) ...

if file_m and file_o:
    df_m_raw = load_data(file_m)
    df_o_raw = load_data(file_o)
    
    if df_m_raw is not None and df_o_raw is not None:
        df_m_raw.columns = [c.strip() for c in df_m_raw.columns]
        df_o_raw.columns = [c.strip() for c in df_o_raw.columns]

        # 1. 회원 정보 전처리
        df_m = df_m_raw[['이메일', '이름', '회원 그룹']].copy()
        df_m['이메일'] = df_m['이메일'].astype(str).str.strip()
        
        # 2. 주문 정보 전처리 (491건 전체 유지)
        df_o = df_o_raw[['주문자 이메일', '상품명', '주문일', '주문자 이름']].copy()
        df_o.columns = ['이메일', '상품명', '주문일', '주문자이름']
        df_o['이메일'] = df_o['이메일'].astype(str).str.strip()

        # 3. 데이터 결합 (how='left'로 변경하여 모든 주문 유지)
        # 주문 내역(df_o)을 기준으로 회원 정보(df_m)를 붙입니다.
        df_merged = pd.merge(df_o, df_m, on='이메일', how='left')

        # 회원 정보가 없는 경우 처리
        df_merged['회원 그룹'] = df_merged['회원 그룹'].fillna("미가입/그룹없음")
        df_merged['이름'] = df_merged['이름'].fillna(df_merged['주문자이름']) # 회원명 없으면 주문자명으로 대체

        # 4. 회원 그룹 분리 및 필터링
        df_merged['회원 그룹'] = df_merged['회원 그룹'].astype(str).str.split(',')
        df_display = df_merged.explode('회원 그룹')
        df_display['회원 그룹'] = df_display['회원 그룹'].str.strip()

        # 제외할 그룹 필터 (이 로직 때문에 숫자가 줄어들 수 있음)
       # exclude_prefixes = ('AI-PPT', 'AI-Literacy')
        # 제외 그룹에 속하더라도 '전체' 보기에서는 포함시키고 싶다면 아래 한 줄을 주석처리하거나 조정하세요.
        df_display_filtered = df_display[~df_display['회원 그룹'].str.startswith(exclude_prefixes)]

        # --- 대시보드 표시 ---
        total_orders = len(df_o_raw) # 원본 주문 건수 (491건)
        matched_orders = len(df_display_filtered) # 필터링 후 건수
        
        st.sidebar.metric("원본 주문 건수", f"{total_orders}건")
        st.sidebar.metric("분석 대상 건수", f"{matched_orders}건")

        # (이후 탭 구성 및 출력 로직은 이전과 동일)
