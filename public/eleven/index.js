const baseUrl = localStorage.getItem('BASE_API_URL');
const authToken = localStorage.getItem('AUTH_TOKEN');
const dom_message = document.querySelector('#message');

const inputTextMessage = document.querySelector('input#textmessage');
const btnRunTTS = document.querySelector('Button#runtts');
const selectVoiceId = document.querySelector('select#voiceid');

export default async () => {
    console.log('start app');

    try {
        const response = await fetch(`${baseUrl}/elevenvoice/about`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
        });
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Failed to get base api', errorText);
            return;
        }
        const data = await response.json();
        console.log('base api:', data);

        dom_message.innerHTML = `Successfully auth to voiceai api`;


    }
    catch (error) {
        console.error('Failed to get base api', error);
        dom_message.innerHTML = `Failed to auth to voiceai api`;
    }

    btnRunTTS.addEventListener('click', async () => {

        const _text = inputTextMessage.value;
        console.log('run tts ', _text);
        try {
            const response = await fetch(`${baseUrl}/elevenvoice/tts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    text: _text,
                    voice_id: selectVoiceId.value,
                })
            });
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Failed to generate TTS', errorText);
                dom_message.innerHTML = `Failed to generate TTS: ${errorText}`;
                return;
            }
            // 반환된 음성 데이터를 Blob으로 변환
            const audioBlob = await response.blob();
            // Blob을 URL로 변환
            const audioUrl = URL.createObjectURL(audioBlob);
            // Audio 객체를 생성하여 재생
            const audio = new Audio(audioUrl);
            audio.play();
            dom_message.innerHTML = `Playing TTS for: "${_text}"`;
        }
        catch (error) {
            console.error('Error in TTS', error);
            dom_message.innerHTML = `Error generating TTS`;
        }

    });
};