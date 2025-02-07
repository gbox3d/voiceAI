import express from 'express';
import cors from 'cors';

export default function (context) {
    const router = express.Router();

    // CORS 설정
    router.use(cors());
    // 파일 전송을 위한 미들웨어 설정
    router.use(express.json({limit:'10mb'})); // JSON 파싱 미들웨어
    router.use(express.text({limit:'10mb'})); // 텍스트 파싱 미들웨어

    // router.use(bodyParser.json({ limit: '100mb' }));

    console.log('setup base router');
    

    // 기본 API 응답
    router.get('/', (req, res) => {
        res.json({ r: 'ok', info: `miso voice API ${context.version}` });
    });


    return router;
}

