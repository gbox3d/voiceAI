import micLibsSetup from '../libs/miclibs.js';
const Context = {
    baseUrl: localStorage.getItem('BASE_API_URL'),
    authToken: localStorage.getItem('AUTH_TOKEN'),
    uploadUrl: 'https://ailab.miso.center:22280/uploads/',
    doms: {},
    selectedDeviceId: null
};

async function Recognize(file) {
    {
        try {
            const response = await fetch(`${Context.baseUrl}/asr/recognize/${file}`, {
                method: 'GET'
            });
            const data = await response.json();
            console.log(data);

            Context.doms.resultText.value = data.text;
        }
        catch (err) {
            console.error('인식 실패:', err);


            Context.doms.resultText.value = '인식 실패' + err;
        }
    }

}

async function updateFileList() {
    //file list
    const response = await fetch(`${Context.baseUrl}/asr/list`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            // 'Authorization': `Bearer ${Context.authToken}`
        }
    });
    const data = await response.json();
    console.log(data);

    while (Context.doms.uploadList.firstChild) {
        Context.doms.uploadList.removeChild(Context.doms.uploadList.firstChild);
    }

    data.files.forEach(file => {
        const _li = document.createElement('li');
        _li.classList.add('w3-bar');
        const _span = document.createElement('span');
        _span.classList.add('w3-bar-item');
        _span.textContent = file;
        _li.appendChild(_span);

        //play button
        const playBtn = document.createElement('button');
        playBtn.classList.add('w3-btn', 'w3-green');
        playBtn.textContent = 'Play';
        playBtn.onclick = async () => {
            const audio = new Audio(`${Context.uploadUrl}${file}`);


            audio.onended = () => {
                console.log('재생 종료');
                audio.remove();
                playBtn.disabled = false;
            }

            audio.onpause = () => {
                console.log('일시 정지');
            }

            audio.onplay = () => {
                console.log('재생 시작');
                playBtn.disabled = true;
            }

            audio.play();
        };
        _li.appendChild(playBtn);

        const RecognizeBtn = document.createElement('button');
        RecognizeBtn.classList.add('w3-btn', 'w3-blue');
        RecognizeBtn.textContent = 'Recognize';
        RecognizeBtn.addEventListener('click', async () => {
            RecognizeBtn.disabled = true;
            RecognizeBtn.textContent = 'Recognizing...';
            await Recognize(file);

            RecognizeBtn.disabled = false;
            RecognizeBtn.textContent = 'Recognize';

        });
        _li.appendChild(RecognizeBtn);

        const deleteBtn = document.createElement('button');
        deleteBtn.classList.add('w3-btn', 'w3-red');
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = async () => {
            try {

                const _ok = confirm('삭제하시겠습니까?');

                if (!_ok) {
                    return;
                }

                const response = await fetch(`${Context.baseUrl}/asr/remove/${file}`, {
                    method: 'GET'
                });

                if (response.ok) {
                    console.log('삭제 성공');
                    _li.remove();
                } else {
                    console.error('삭제 실패:', response.statusText);
                }
            } catch (err) {
                console.error('삭제 실패:', err);
            }
        };
        _li.appendChild(deleteBtn);

        Context.doms.uploadList.appendChild(_li);
    });
}


function micSetup() {
    // 녹음 관련 변수
    let isRecording = false;
    let mediaRecorder; // outer variable
    let stream;

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
    
    // 선택된 마이크 장치 변경 시 업데이트
    Context.doms.micSelect.addEventListener('change', (evt) => {
        Context.selectedDeviceId = evt.target.value;
        console.log("선택된 마이크:", Context.selectedDeviceId);
    });

    updateMicList();

    // 녹음 시작 함수
    async function startRecording() {
        try {
            // 선택된 마이크 deviceId를 사용하여 마이크 권한 요청
            const constraints = {
                audio: { deviceId: Context.selectedDeviceId ? { exact: Context.selectedDeviceId } : undefined }
            };
            stream = await navigator.mediaDevices.getUserMedia(constraints);
            const mimeType = Context.miclibs.mimeType;
            const options = mimeType ? { mimeType } : undefined;
            mediaRecorder = new MediaRecorder(stream, options);
            let chunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                // 녹음된 데이터를 blob으로 생성. MIME 타입은 사용한 옵션에 따라 결정
                const blob = new Blob(chunks, { type: mimeType || 'audio/webm' });
                const url = URL.createObjectURL(blob);
                console.log('녹음된 파일 URL:', url);
                // 업로드 함수 호출
                await uploadAudio(blob, mimeType);

                await updateFileList();
            };

            mediaRecorder.start();
            console.log("녹음 시작");
        } catch (err) {
            console.error("녹음 시작 중 에러:", err);
        }
    }

    // 녹음 중지 함수
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            console.log("녹음 중지");
        }
    }

    // 오디오 파일 업로드 함수
    async function uploadAudio(blob, mimeType) {
        const formData = new FormData();
        // 파일 확장자는 MIME 타입에 따라 다르게 설정 (여기서는 webm 또는 ogg)
        let extension = 'webm';
        if (mimeType && mimeType.indexOf('ogg') !== -1) {
            extension = 'ogg';
        }
        const file = new File([blob], `recording.${extension}`, { type: mimeType || 'audio/webm' });
        formData.append('audio', file);

        try {
            const response = await fetch(`${Context.baseUrl}/asr/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            console.log("업로드 결과:", data);
        } catch (err) {
            console.error("업로드 실패:", err);
        }
    }

    // 녹음 버튼 클릭 이벤트 리스너 등록
    Context.doms.btnRecord.addEventListener('click', async (evt) => {
        if (!isRecording) {
            evt.target.innerText = 'Stop Recording';
            console.log('녹음 시작 요청');
            await startRecording();
        } else {
            evt.target.innerText = 'Start Recording';
            console.log('녹음 중지 요청');
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
        uploadList: document.querySelector('#uploadList ul'),
        resultText: document.querySelector('#result'),
        mediaType: document.querySelector('#mediaType')

    };

    console.log('start app');

    // ASR API 테스트(GET 요청)
    try {
        const response = await fetch(`${Context.baseUrl}/asr`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        console.log(data);
    } catch (error) {
        console.error("GET /asr 실패:", error);
    }

    // 업로드된 파일 목록 불러오기
    updateFileList();

    const miclibs = await micLibsSetup();
    Context.miclibs = miclibs;
    console.log(miclibs);

    if (miclibs.isSupported) {
        Context.doms.mediaType.innerText = `This Browser Supported Media Type : ${miclibs.mimeType}`;
        // updateMicList(); // 마이크 목록 업데이트
        micSetup(); // 녹음 기능 설정
    }
    else {
        console.error("이 브라우저는 녹음 기능을 지원하지 않습니다.");
        Context.doms.btnRecord.disabled = true;
        Context.doms.btnRecord.innerText = '녹음 기능 미지원';
        return;
    }







};
