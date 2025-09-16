# filename: pages/3_🔊_TTS_서버.py
# author: gbox3d
# created: 2025-07-31
# description: TTS Server status checking page

import streamlit as st
import sys
import os
from utils.ServerChecker import ServerChecker, run_async

from dotenv import load_dotenv

load_dotenv()
TTS_DIR = os.getenv('TTS_DIR')

# 세션이 시작되었는지 확인하는 'flag' 키를 사용합니다.
if 'initialized' not in st.session_state:
    # --- 이 블록은 세션 당 딱 한 번만 실행됩니다 (새로고침 포함) ---

    # 1. .env 파일을 강제로 다시 읽어 메모리(os.environ)를 최신 상태로 업데이트합니다.
    load_dotenv(override=True)    
    load_dotenv(os.path.join(TTS_DIR, '.env'), override=True)

    # 2. 최신 환경 변수 값으로 session_state를 '초기화'합니다.
    st.session_state.tts_port = int(os.getenv('TTS_PORT', 2501))
    
    # 3. 초기화가 완료되었음을 표시합니다.
    st.session_state.initialized = True



st.set_page_config(
    page_title="TTS 서버 - 서버 상태 확인",
    page_icon="🔊",
    layout="wide"
)

st.title("🔊 TTS 서버 상태 확인")
st.markdown(f"**Text-to-Speech** 서버의 상태를 상세히 확인합니다. 현재 포트: {st.session_state.tts_port}")
st.markdown("---")


checker = ServerChecker()


# 연결 테스트 섹션
st.header("🔍 연결 테스트")

if st.button("🚀 TTS 서버 상태 확인", type="primary", use_container_width=True):
    with st.spinner("TTS 서버에 연결 중..."):
        success, message, response_time = run_async(
            checker.check_tts_server(
                'localhost', 
                st.session_state.tts_port
            )
        )
    
    st.subheader("📊 테스트 결과")
    
    if success:
        st.success("✅ 연결 성공!")
        
        # 성공 메트릭
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("상태", "🟢 정상")
        with col_b:
            st.metric("응답 시간", f"{response_time:.3f}초")
        
        
        # 성능 평가
        if response_time < 0.1:
            st.success("🏃‍♂️ **매우 빠른 응답속도** - 우수한 네트워크 상태")
        elif response_time < 0.5:
            st.info("🚶‍♂️ **양호한 응답속도** - 정상적인 네트워크 상태")
        else:
            st.warning("🐌 **느린 응답속도** - 네트워크 상태 확인 필요")
        
    else:
        st.error("❌ 연결 실패!")
        
        # 실패 메트릭
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("상태", "🔴 오류")
        with col_b:
            st.metric("서버", f"{st.session_state.tts_host}:{st.session_state.tts_port}")
        
        st.warning(f"⚠️ **오류 내용**: {message}")
st.markdown("---")

