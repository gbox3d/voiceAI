# filename: pages/2_🎤_ASR_서버.py
# author: gbox3d
# created: 2025-07-31
# description: ASR Server status checking page

import streamlit as st
import sys
import os

from utils.ServerChecker import ServerChecker, run_async

import dotenv

dotenv.load_dotenv()
ASR_DIR = os.getenv('ASR_DIR', '/home/gbox3d/work/MiracleASRServer')

# 세션이 시작되었는지 확인하는 'flag' 키를 사용합니다.
if 'initialized' not in st.session_state:
    # --- 이 블록은 세션 당 딱 한 번만 실행됩니다 (새로고침 포함) ---

    # 1. .env 파일을 강제로 다시 읽어 메모리(os.environ)를 최신 상태로 업데이트합니다.
    dotenv.load_dotenv(override=True)    
    dotenv.load_dotenv(os.path.join(ASR_DIR, '.env'), override=True)

    # 2. 최신 환경 변수 값으로 session_state를 '초기화'합니다.
    st.session_state.asr_port = int(os.getenv('ASR_PORT'))
    st.session_state.asr_checkcode = int(os.getenv('ASR_CHECKCODE'))
    st.session_state.min_text_length = int(os.getenv('MIN_TEXT_LENGTH', 10))
    st.session_state.no_voice_text = os.getenv('NO_VOICE_TEXT', '음성이 감지되지 않았습니다.')
    
    st.session_state.model_id = os.getenv('MODEL_ID', 'openai/whisper-large-v3-turbo')
    st.session_state.model_dir = os.getenv('MODEL_DIR', './models/whisper-large-v3-turbo')
    st.session_state.timeout = int(os.getenv('ASR_TIMEOUT', 10))
    
    # 3. 초기화가 완료되었음을 표시합니다.
    st.session_state.initialized = True
    print("ASR 페이지 초기화 완료")
else:
    # --- 이 블록은 세션이 이미 초기화된 경우 실행됩니다 ---
    print("ASR 페이지가 이미 초기화되었습니다.")
    

st.set_page_config(
    page_title="ASR 서버 - 서버 상태 확인 ",
    page_icon="🎤",
    layout="wide"
)

st.title("🎤 ASR 서버 상태 확인")
st.markdown("**Speech-to-Text** 서버의 상태를 상세히 확인합니다.")
st.markdown("---")

    

checker = ServerChecker()

# 서버 정보 카드
with st.container():
    st.header("ℹ️ ASR 서버 정보")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"""
        **🤖 엔진**  
        {st.session_state.model_id}
        """)
    
    with col2:
        st.info("""
        **🎵 지원 포맷**  
        WAV, MP3, WebM, MP4
        """)
    
    with col3:
        st.info(f"""
        **🔧 기본 설정**  
        포트: {st.session_state.asr_port}                  
        """)

st.markdown("---")

# 서버 설정 섹션
st.header("⚙️ 서버 연결 설정")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("기본 설정")
    
    
    st.session_state.asr_port = st.number_input(
        "포트 번호", 
        min_value=1, 
        max_value=65535, 
        value=st.session_state.asr_port,
        help="ASR 서버가 리스닝하는 포트 번호"
    )
    
    
    st.session_state.min_text_length = st.number_input(
        "최소 텍스트 길이", 
        min_value=0, 
        value=st.session_state.min_text_length,
        help="인식된 텍스트의 최소 길이"
    )    
    st.session_state.no_voice_text = st.text_input(
        "음성 없음 텍스트", 
        value=st.session_state.no_voice_text,
        help="음성이 감지되지 않았을 때 표시할 텍스트"
    )
    

with col2:
    st.subheader("설정 관리")
    
    # 설정 저장 버튼
    if st.button("💾 설정 저장", use_container_width=True):
        env_path = os.path.join(ASR_DIR, '.env')

        # 기존 .env 파일 읽기
        env_content = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.readlines()
        
        # 업데이트할 설정들
        updates = {            
            'ASR_PORT': str(st.session_state.asr_port), 
            # 'ASR_CHECKCODE': str(st.session_state.asr_checkcode),
            'MIN_TEXT_LENGTH': str(st.session_state.min_text_length),
            'NO_VOICE_TEXT': st.session_state.no_voice_text            
        }
        
        # 기존 설정 업데이트 또는 새로 추가
        updated_keys = set()
        for i, line in enumerate(env_content):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in updates:
                    env_content[i] = f"{key}={updates[key]}\n"
                    updated_keys.add(key)
        
        # 새로운 설정 추가
        for key, value in updates.items():
            if key not in updated_keys:
                env_content.append(f"{key}={value}\n")
        
        # .env 파일에 저장
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(env_content)
            st.success("✅ 설정이 저장되었습니다!")
            st.info(f"저장 위치: {env_path}")
        except Exception as e:
            st.error(f"❌ 설정 저장 실패: {e}")
            
        print(f"update min text length: {st.session_state.min_text_length}")
    
    

st.markdown("---")

# 연결 테스트 섹션
st.header("🔍 연결 테스트")
timeout = st.session_state.timeout
checker.timeout = timeout
    
if st.button("🚀 ASR 서버 상태 확인", type="primary", use_container_width=True):
    with st.spinner("ASR 서버에 연결 중..."):
        success, message, response_time = run_async(
            checker.check_asr_server(
                host='localhost',                
                port = st.session_state.asr_port, 
                checkcode= st.session_state.asr_checkcode
            )
        )
    st.subheader("📊 테스트 결과")
    
    if success:
        st.success("✅ 연결 성공!")
        
        # 성공 메트릭
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("상태", "🟢 정상")
        with col_b:
            st.metric("응답 시간", f"{response_time:.3f}초")
        
        
        st.info(f"📝 **세부 정보**: {message}")
        
    else:
        st.error("❌ 연결 실패!")
        
        # 실패 메트릭
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("상태", "🔴 오류")
        with col_b:
            st.metric("서버", f"{st.session_state.asr_host}:{st.session_state.asr_port}")
        
        st.warning(f"⚠️ **오류 내용**: {message}")
        
if st.button("🎤 음성 파일 인식 테스트", use_container_width=True):
    audio_file = "assets/hi_kor.wav" # 테스트할 오디오 파일 경로
    with st.spinner(f"'{audio_file}' 파일을 전송하여 음성 인식 테스트 중..."):
        success, message, response_time = run_async(
            checker.check_asr_transcription(
                host='localhost',
                port=st.session_state.asr_port,
                checkcode=st.session_state.asr_checkcode,
                audio_filepath=audio_file
            )
        )
    
    if success:
        st.success(f"✅ 인식 성공! (응답 시간: {response_time:.3f}초)")
        st.info(f"**인식 결과**: {message}")
    else:
        st.error(f"❌ 인식 실패!")
        st.warning(f"**오류 내용**: {message}")

# 현재 설정 표시
st.markdown("---")
st.header("📋 현재 설정 정보")

col1, col2 = st.columns(2)

with col1:
    st.subheader("연결 설정")
    st.code(f"""
포트: {st.session_state.asr_port}
타임아웃: {timeout}초
    """)

with col2:
    st.subheader("서버 정보")
    st.code(f"""
모델: {st.session_state.model_id}
최소 텍스트 길이: {st.session_state.min_text_length}
음성 없음 텍스트: {st.session_state.no_voice_text}
Server 디렉토리: {st.session_state.model_dir}
    """)

# 네비게이션 버튼
st.markdown("---")
st.header("🧭 페이지 이동")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 대시보드로 이동"):
        st.switch_page("pages/1_📊_대시보드.py")

with col2:
    if st.button("🔊 TTS 서버로 이동"):
        st.switch_page("pages/3_🔊_TTS_서버.py")

with col3:
    if st.button("🏠 홈으로 돌아가기"):
        st.switch_page("main.py")

# 푸터
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666;'>
    🎤 <strong>ASR 서버 상태 확인 port {st.session_state.asr_port}</strong> | {st.session_state.model_id}<br>
    실시간 음성인식 서버 모니터링
</div>
""", unsafe_allow_html=True)