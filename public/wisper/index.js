
import lamejs from 'lamejs';

const Context = {
    baseUrl: 'https://ailab.miso.center:22281/api/v1',
    authToken: '112u642l!v*qw6hm)fz_%4zx9-je($t=hlb$^yw+6^h$a#!)-(',
    doms : {}
}


export default async () => {

    Context.doms = {
        btnRecord: document.querySelector('button#record')
    }

    console.log('start app');
    const response = await fetch(`${Context.baseUrl}/asr`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        }
    });
    const data = await response.json();
    console.log(data);

    let isRecording = false;
    Context.doms.btnRecord.addEventListener('click', async (evt) => {

        if (isRecording) {
            console.log('start recording');
            evt.target.innerText = 'Stop Recording';
        } else {
            console.log('stop recording');
            evt.target.innerText = 'Start Recording';
            
        }
        isRecording = !isRecording;


    });

    
};