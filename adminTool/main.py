# filename: main.py
# author: gbox3d (modified for multipage)
# created: 2025-07-31
# description: Main page for Streamlit multipage server status checker

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="서버 관리자 페이지",
    page_icon="🔧",
    layout="wide"
)



# 빠른 시작 섹션
st.header("🔧 서버 관리자 페이지")

col1, col2 = st.columns(2)


with col1:
    st.subheader("🎤 ASR 서버")
    if st.button("ASR 페이지로 이동"):
        st.switch_page("pages/1_ASR.py")

with col2:
    st.subheader("🔊 TTS 서버")
    if st.button("TTS 페이지로 이동"):
        st.switch_page("pages/2_TTS.py")


# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    🔧 <strong>서버 상태 확인 도구</strong> | ASR & TTS Server Status Checker<br>
    Made with ❤️ using Streamlit
</div>
""", unsafe_allow_html=True)