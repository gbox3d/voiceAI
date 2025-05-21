
const Context = {

    ttsBaseUrl: localStorage.getItem('BASE_TTSAPI_URL') || '',
    sttBaseUrl: localStorage.getItem('BASE_STTAPI_URL') || '',
    doms: {},

}

export default async () => {
    console.log('start app');

    // try {
    //     const response = await fetch(`${Context.baseApiUrl}/auth`, {
    //         method: 'GET',
    //         headers: { 'Content-Type': 'application/json' ,
    //         'Authorization': `Bearer ${Context.authToken}`
    //         }
    //     });
    //     const data = await response.json();
    //     console.log(data);


    // }
    // catch (error) {
    //     console.error('error:', error);
    // }  


    Context.doms = {
        input_STTapiUrl: document.querySelector('#apiSTTBaseUrl'),
        input_TTSapiUrl: document.querySelector('#apiTTSBaseUrl'),
        btn_save: document.querySelector('#save')

    }

    Context.doms.input_STTapiUrl.value = Context.sttBaseUrl;
    Context.doms.input_TTSapiUrl.value = Context.ttsBaseUrl;

    function normalizeUrl(url) {
        return url
            .trim()               // 앞뒤 공백 제거
            .replace(/\s+/g, "")  // 내부 공백 제거 (필요 없으면 지워도 됩니다)
            .replace(/\/+$/, ""); // 후행 '/' 제거
    }

    Context.doms.btn_save.addEventListener('click', async () => {

        const sttBaseUrl =  normalizeUrl(Context.doms.input_STTapiUrl.value);
        const ttsBaseUrl =  normalizeUrl(Context.doms.input_TTSapiUrl.value);

        localStorage.setItem('BASE_TTSAPI_URL', ttsBaseUrl);
        localStorage.setItem('BASE_STTAPI_URL', sttBaseUrl);

        // update Context
        Context.doms.input_STTapiUrl.value = sttBaseUrl;
        Context.doms.input_TTSapiUrl.value = ttsBaseUrl;

        alert('API URL saved successfully');
    }
    );


};