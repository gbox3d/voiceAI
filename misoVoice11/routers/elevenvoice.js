import express from 'express';

import AuthSetup from './auth.js';
import fetch from 'node-fetch';


export default function (context) {

    const router = express.Router();

    const authMiddleware = AuthSetup(context);

    console.log('setup elevenvoice router');

    // 기본 API 응답
    router.get('/about', authMiddleware, (req, res) => {
        res.json({
            r: 'ok', info: {
                api_key: context.eleven_api_key,
                version: context.version
            }
        });
    });

    // POST /tts 엔드포인트: 텍스트를 음성으로 변환하여 MP3 파일을 반환
    router.post('/tts', authMiddleware, async (req, res) => {
        try {
            const { text, voice_id, model_id, output_format } = req.body;
            const ttsVoiceId = voice_id || "s07IwTCOrCDCaETjUVjx"; // 기본 보이스 아이디
            const ttsModelId = model_id || "eleven_multilingual_v2"; // 다국어 지원 모델
            const ttsOutputFormat = output_format || "mp3_44100_128"; // 출력 포맷

            if (!text) {
                return res.status(400).json({ error: "텍스트가 필요합니다." });
            }

            const apiUrl = `https://api.elevenlabs.io/v1/text-to-speech/${ttsVoiceId}`;
            const payload = {
                text: text,
                model_id: ttsModelId,
                output_format: ttsOutputFormat
            };

            const response = await fetch(apiUrl, {
                method: "POST",
                headers: {
                    "xi-api-key": context.eleven_api_key,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                return res.status(response.status).json({ error: errorText });
            }

            // 응답 데이터를 ArrayBuffer로 읽고 Buffer 객체로 변환하여 전송
            const arrayBuffer = await response.arrayBuffer();
            const buffer = Buffer.from(arrayBuffer);
            res.setHeader("Content-Type", "audio/mpeg");
            res.send(buffer);
        } catch (error) {
            console.error("Error in /tts:", error);
            res.status(500).json({ error: "Internal Server Error" });
        }
    });



    return router;
}

