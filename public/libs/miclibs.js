
function checkMediaDevice() {
    // 녹음 기능 지원 여부 체크
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
        console.error("이 브라우저는 녹음 기능을 지원하지 않습니다.");
        return false;
    } 
    else {
        console.log("이 브라우저는 녹음 기능을 지원합니다.");
        return true;
    }
}


// 지원하는 MIME 타입을 확인하는 함수
function getSupportedMimeType() {
    if (MediaRecorder.isTypeSupported('audio/ogg; codecs=opus')) {
        return 'audio/ogg; codecs=opus';
    } else if (MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
        return 'audio/webm; codecs=opus';
    } else if (MediaRecorder.isTypeSupported('audio/mp4')) { // iOS Safari 지원
        return 'audio/mp4';
    } 
    else {
        console.warn("지원되는 OGG/WebM opus MIME 타입이 없습니다. 기본값을 사용합니다.");

        return 'none';
    }
}

export default async () => {

    const isSupported = checkMediaDevice();
    const mimeType = getSupportedMimeType();


    return {
        isSupported,
        mimeType
    }
}
