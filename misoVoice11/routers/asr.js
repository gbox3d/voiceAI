/*
파일명 : asr.js
기능 : ASR 서비스 API 라우터
작성자 : gbox3d
작성일 : 2025-2-14
*/

// routers/asr.js
import express from 'express';
import multer from 'multer';
import path from 'path';


export default function (context) {
    const router = express.Router();

    // .env에서 지정된 업로드 경로를 사용 (기본값은 './uploads'로 설정)
    const uploadPath = process.env.UPLOAD_PATH || './uploads';

    // multer 디스크 스토리지 설정
    const storage = multer.diskStorage({
        destination: function (req, file, cb) {
            cb(null, uploadPath);
        },
        filename: function (req, file, cb) {
            // 파일 이름: 현재 타임스탬프와 원본 파일명을 조합
            const ext = path.extname(file.originalname);
            const basename = path.basename(file.originalname, ext);
            const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
            cb(null, `${basename}-${uniqueSuffix}${ext}`);
        }
    });

    // 파일 업로드 미들웨어 생성 (여기서는 단일 파일 업로드, 필드명은 'audio'로 설정)
    const upload = multer({
        storage: storage,
        fileFilter: (req, file, cb) => {
            // mp3 파일만 허용 (MIME 타입 체크)
            if (file.mimetype === 'audio/mpeg' || file.mimetype === 'audio/mp3') {
                cb(null, true);
            } else {
                cb(new Error('mp3 파일만 업로드할 수 있습니다.'), false);
            }
        }
    });

    // GET /api/v1/asr 엔드포인트: 테스트용 API
    router.get('/', (req, res) => {
        res.json({ message: 'ASR 서비스 API',version : context.version });
    });

    // POST /api/v1/asr/upload 엔드포인트: 파일 업로드 처리
    router.post('/upload', upload.single('audio'), (req, res) => {
        if (!req.file) {
            return res.status(400).json({ error: '파일이 업로드되지 않았습니다.' });
        }
        res.json({
            message: '파일 업로드 성공',
            filePath: req.file.path, // 저장된 파일 경로 반환
            fileName: req.file.filename
        });
    });

    return router;
}
