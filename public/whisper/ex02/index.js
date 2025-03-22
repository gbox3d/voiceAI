import micLibsSetup from '../../libs/miclibs.js';

const Context = {
    // baseUrl: 'https://ailab.miso.center:22281/api/v1',
    authToken: localStorage.getItem('AUTH_TOKEN'),
    doms: {},
    selectedDeviceId: null
};

function addLog(test) {

    const logTxt = document.createElement('p');
    logTxt.textContent = test;
    Context.doms.logTxt.appendChild(logTxt);

}


// 마이크 장치 목록 불러오기 및 select 요소 채우기
async function updateMicList() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter(device => device.kind === 'audioinput');
        Context.doms.micSelect.innerHTML = '';
        audioInputs.forEach(device => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `마이크 ${Context.doms.micSelect.length + 1}`;
            Context.doms.micSelect.appendChild(option);
        });
        // 기본 선택한 deviceId
        if (audioInputs.length > 0) {
            Context.selectedDeviceId = audioInputs[0].deviceId;
        }
    } catch (err) {
        console.error("마이크 목록 업데이트 에러:", err);
    }
}

function micSetup() {
    let isRecording = false;
    let _mediaRecorder;
    let Stream;
    let Chunks = [];

    // Test 녹음 시작 함수
    async function startRecording() {
        try {
            addLog('Test 녹음 시작 중...');
            // 선택된 마이크(없으면 기본) 사용하여 오디오 스트림 얻기
            const constraints = {
                audio: { 
                    deviceId: Context.selectedDeviceId 
                        ? { exact: Context.selectedDeviceId } 
                        : undefined 
                }
            };

            Stream = await navigator.mediaDevices.getUserMedia(constraints);
            const mimeType = Context.miclibs.mimeType;
            const options = mimeType ? { mimeType } : undefined;
            _mediaRecorder = new MediaRecorder(Stream, options);
            Chunks = [];
            addLog('Test 녹음 준비 완료');

            _mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    Chunks.push(e.data);
                    addLog('Test 녹음 중...');
                }
            };

            // 녹음이 정지되었을 때 호출되는 부분
            _mediaRecorder.onstop = async () => {
                const blob = new Blob(Chunks, { type: mimeType || 'audio/webm' });
                const url = URL.createObjectURL(blob);
                addLog(`Test 녹음 완료 -> blob url: ${url}`);

                // ==============================
                // 1) ASR 요청 (transcribe) 부분
                // ==============================
                try {
                    // Blob 데이터를 FormData로 감싸서 전송 준비
                    const formData = new FormData();
                    // 서버가 파일 필드명을 'audio'로 받으므로 'audio'로 설정
                    // 파일명은 편의를 위해 'recorded' 같은 임의의 이름을 사용
                    formData.append('audio', blob, 'recorded.webm');

                    // fetch를 통해 서버에 전송
                    const response = await fetch(`${Context.baseUrl}/asr/transcribe`, {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        // HTTP 200이 아닌 경우 오류 처리
                        const errMsg = await response.text();
                        addLog(`[ERROR] ASR 변환 요청 실패: ${errMsg}`);
                        return;
                    }

                    // JSON으로 응답 파싱
                    const result = await response.json();
                    if (result.error) {
                        addLog(`[ERROR] ASR 변환 실패: ${result.error}`);
                    } else {
                        // 정상적으로 텍스트가 반환된 경우
                        const recognizedText = result.text;
                        addLog(`[INFO] ASR 변환 결과: ${recognizedText}`);
                        Context.doms.resultTxt.innerText = recognizedText;
                    }
                } catch (err) {
                    console.error('ASR 요청 중 에러:', err);
                    addLog(`[ERROR] ASR 요청 중 에러: ${err.message}`);
                }
                // ==============================

            };

            _mediaRecorder.start();
            console.log("Test 녹음 시작");
            addLog('Test 녹음 시작');

        } catch (err) {
            console.error("Test 녹음 시작 중 에러:", err);
            alert("Test 녹음 시작 중 에러 발생" + err);
        }
    }

    function stopRecording() {
        if (_mediaRecorder && _mediaRecorder.state !== 'inactive') {
            _mediaRecorder.stop();
            if (Stream) {
                Stream.getTracks().forEach(track => track.stop());
            }
            console.log("Test 녹음 중지");
        }
    }

    Context.doms.btnRecord.addEventListener('click', async (evt) => {
        if (!isRecording) {
            evt.target.innerText = 'Stop Test';
            console.log('Test 녹음 시작 요청');
            addLog('Test 녹음 시작 요청');
            await startRecording();
        } else {
            evt.target.innerText = 'Start Test';
            console.log('Test 녹음 중지 요청');
            addLog('Test 녹음 중지 요청');
            stopRecording();
        }
        isRecording = !isRecording;
    });
}


export default async () => {
    // DOM 요소 초기화
    Context.doms = {
        btnRecord: document.querySelector('button#record'),
        micSelect: document.querySelector('select#micSelect'),
        SpeechList: document.querySelector('#testList ul'),
        mediaType : document.querySelector('#mediaType'),
        logTxt : document.querySelector('#log'),
        resultTxt : document.querySelector('#resultTxt')
    };

    console.log('start app');
    addLog('start app v1.0');

    Context.baseUrl =  `${location.protocol}//${location.hostname}:22281/api/v1`;

    console.log('Context.baseUrl : ', Context.baseUrl);


    const miclibs = await micLibsSetup();
    Context.miclibs = miclibs;
    console.log(miclibs);

    if(miclibs.isSupported) {
        Context.doms.mediaType.innerText = `This Browser Supported Media Type : ${miclibs.mimeType}`;
        updateMicList(); // 마이크 목록 업데이트
        micSetup(); // 녹음 기능 설정
    }
    else {
        console.error("이 브라우저는 녹음 기능을 지원하지 않습니다.");
        Context.doms.btnRecord.disabled = true;
        Context.doms.btnRecord.innerText = '녹음 기능 미지원';
        return;
    }

};
