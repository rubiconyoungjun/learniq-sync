import streamlit as st
import pandas as pd
import json
import io

st.set_page_config(page_title="LearnIQ B2B Dashboard", layout="wide")
st.title("🏛️ LearnIQ 기관별 통합 관리 시스템")

# 파일 로드 함수 (CSV, XLSX, XLS 지원)
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            # CSV의 경우 인코딩 문제 방지를 위해 cp949와 utf-8-sig 시도
            try:
                return pd.read_csv(file, encoding='utf-8-sig')
            except:
                return pd.read_csv(file, encoding='cp949')
        else:
            # xlsx, xls 모두 지원
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return None

# 회원 데이터 파싱 함수 (회원목록용)
def parse_member_info(row):
    # 1. 소속기관(그룹) 판별
    email = str(row.get('주문자 이메일') or row.get('email') or "")
    group = "미지정(일반)"
    
    if 'yonsei.ac.kr' in email: group = "연세대학교"
    elif 'kaist.ac.kr' in email: group = "KAIST"
    elif 'klri.re.kr' in email: group = "한국법제연구원"
    elif 'rubicontech.co.kr' in email: group = "루비콘테크"
    
    # 2. 이름 추출 (JSON 구조 및 일반 컬럼 대응)
    name = row.get('주문자 이름') or row.get('name') or "이름없음"
    if 'orderer' in row and pd.notnull(row['orderer']):
        try:
            orderer_data = json.loads(row['orderer'].replace("''", '"'))
            name = orderer_data.get('name', name)
            email = orderer_data.get('email', email)
        except: pass

    # 3. 가입일 및 로그인 횟수
    reg_date = row.get('주문일') or row.get('reg_date') or "-"
    login_cnt = row.get('로그인 횟수') or row.get('login_cnt') or 0
    
    return pd.Series({
        '소속기관': group,
        '이름': name,
        '가입일': reg_date,
        '로그인 횟수': login_cnt,
        '이메일': email
    })

# 사이드바 설정
st.sidebar.header("📁 데이터 업로드")
st.sidebar.info("CSV, XLSX, XLS 파일을 모두 지원합니다.")
file_m = st.sidebar.file_uploader("1. 회원 목록 파일 업로드", type=['csv', 'xlsx', 'xls'])
file_o = st.sidebar.file_uploader("2. 주문 내역 파일 업로드", type=['csv', 'xlsx', 'xls'])

if file_m and file_o:
    with st.spinner('데이터 통합 분석 중...'):
        df_m_raw = load_data(file_m)
        df_o_raw = load_data(file_o)
        
        if df_m_raw is not None and df_o_raw is not None:
            # 회원 정보 정리
            df_m = df_m_raw.apply(parse_member_info, axis=1)
            
            # 주문 정보 정리 (강좌명 콤마 합치기)
            # 샘플 파일 기준 '주문자 이메일'과 '상품명' 사용
            email_col = '주문자 이메일' if '주문자 이메일' in df_o_raw.columns else 'email'
            prod_col = '상품명' if '상품명' in df_o_raw.columns else 'prod_name'
            
            if email_col in df_o_raw.columns and prod_col in df_o_raw.columns:
                df_o_clean = df_o_raw.groupby(email_col)[prod_col].apply(
                    lambda x: ", ".join(list(set(str(i) for i in x if pd.notnull(i))))
                ).reset_index()
                df_o_clean.columns = ['이메일', '주문 강좌']
                
                # 데이터 병합
                df_final = pd.merge(df_m, df_o_clean, on='이메일', how='left')
                df_final['주문 강좌'] = df_final['주문 강좌'].fillna("미신청")
                
                # --- 화면 출력 ---
                tab1, tab2 = st.tabs(["📋 상세 관리 명단", "📊 기관별 통계"])
                
                with tab1:
                    groups = ["전체"] + sorted(df_final['소속기관'].unique().tolist())
                    sel_group = st.selectbox("조회할 소속기관(그룹) 선택", groups)
                    
                    view_df = df_final if sel_group == "전체" else df_final[df_final['소속기관'] == sel_group]
                    
                    # 5대 핵심 컬럼 출력
                    display_cols = ['소속기관', '이름', '가입일', '로그인 횟수', '주문 강좌']
                    st.subheader(f"📍 {sel_group} 수강 현황")
                    st.dataframe(view_df[display_cols], use_container_width=True)
                    
                    # 다운로드 버튼
                    csv = view_df[display_cols].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 현재 리스트 CSV 다운로드", csv, f"{sel_group}_list.csv", "text/csv")

                with tab2:
                    st.subheader("🏢 기관별 인원 요약")
                    summary = df_final.groupby('소속기관')['이름'].count().reset_index()
                    summary.columns = ['소속기관', '인원수(명)']
                    st.table(summary)
            else:
                st.error("주문 파일에서 '이메일' 또는 '상품명' 컬럼을 찾을 수 없습니다.")
else:
    st.info("사이드바에 두 파일을 모두 업로드하면 대시보드가 활성화됩니다.")
