import micLibsSetup from '../../libs/miclibs.js';

const Context = {
    baseUrl: localStorage.getItem('BASE_API_URL'),
    authToken: localStorage.getItem('AUTH_TOKEN'),
    uploadUrl: 'https://ailab.miso.center:22280/uploads/',
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
                    deviceId: Context.selectedDeviceId ? { exact: Context.selectedDeviceId } : undefined 
                }
            };

            Stream = await navigator.mediaDevices.getUserMedia(constraints);
            const mimeType = getSupportedMimeType();
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

            _mediaRecorder.onstop = () => {
                const blob = new Blob(Chunks, { type: mimeType || 'audio/webm' });
                const url = URL.createObjectURL(blob);
                console.log('Test 녹음된 파일 URL:', url);
                addLog('Test 녹음 완료');

                // 오디오 재생 요소 생성
                const audioEl = document.createElement('audio');
                audioEl.controls = true;
                audioEl.src = url;
                // 페이지에 추가 (원하는 위치에 appendChild)
                document.body.appendChild(audioEl);

                // 다운로드 링크 생성
                const downloadLink = document.createElement('a');

                downloadLink.classList.add('w3-btn', 'w3-blue');

                let extension = 'webm';
                if (mimeType && mimeType.indexOf('ogg') !== -1) {
                    extension = 'ogg';
                }
                downloadLink.href = url;
                downloadLink.download = `test_recording.${extension}`;
                downloadLink.textContent = 'Download Test Recording';

                //delete button
                const deleteBtn = document.createElement('button');
                deleteBtn.classList.add('w3-btn', 'w3-red');
                deleteBtn.textContent = 'Delete';
                deleteBtn.onclick = () => {
                    audioEl.remove();
                    downloadLink.remove();
                    deleteBtn.remove();
                };

                const _li = document.createElement('li');

                _li.classList.add('w3-bar');
                _li.appendChild(audioEl);
                _li.appendChild(downloadLink);
                downloadLink.classList.add('w3-bar-item');
                _li.appendChild(deleteBtn);
                deleteBtn.classList.add('w3-bar-item');
                Context.doms.SpeechList.appendChild(_li);
            };

            _mediaRecorder.start();
            console.log("Test 녹음 시작");
            addLog('Test 녹음 시작');

        } catch (err) {
            console.error("Test 녹음 시작 중 에러:", err);
            alert("Test 녹음 시작 중 에러 발생" , err);
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
            console.log('Test 녹음 중지 요청');
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
        logTxt : document.querySelector('#log')
    };

    console.log('start app');
    addLog('start app');


    const miclibs = await micLibsSetup();
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


    // // 녹음 기능 지원 여부 체크
    // if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
    //     console.error("이 브라우저는 녹음 기능을 지원하지 않습니다.");
    //     Context.doms.btnRecord.disabled = true;
    //     Context.doms.btnRecord.innerText = '녹음 기능 미지원';
    //     return;
    // } else {

    //     const mediaType = getSupportedMimeType();
    //     console.log("이 브라우저는 녹음 기능을 지원합니다. " , mediaType);
    //     Context.doms.mediaType.innerText = `This Browser Supported Media Type : ${mediaType}`;
    //     updateMicList(); // 마이크 목록 업데이트
    //     micSetup(); // 녹음 기능 설정
    // }
    
};
