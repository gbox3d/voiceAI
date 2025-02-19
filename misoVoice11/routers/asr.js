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
import fs from 'fs-extra';

import AuthSetup from './auth.js';


export default function (context) {

    const router = express.Router();
    const authMiddleware = AuthSetup(context);

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
            const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9) + `_${req.username ? req.username : 'unknown'}`;

            console.log(`upload file : ${basename}-${uniqueSuffix}${ext}`);

            cb(null, `${basename}-${uniqueSuffix}${ext}`);
        }
    });

    // 파일 업로드 미들웨어 생성 (여기서는 단일 파일 업로드, 필드명은 'audio'로 설정)
    const upload = multer({
        storage: storage,
        fileFilter: (req, file, cb) => {
            // mp3 파일만 허용 (MIME 타입 체크)
            if (file.mimetype === 'audio/mpeg' ||
                file.mimetype === 'audio/mp3' ||
                file.mimetype === 'audio/ogg' ||
                file.mimetype === 'audio/webm'
            ) {
                cb(null, true);
            } else {
                cb(new Error('mp3 파일만 업로드할 수 있습니다.'), false);
            }
        }
    });

    // GET /api/v1/asr 엔드포인트: 테스트용 API
    router.get('/', (req, res) => {
        res.json({ message: 'ASR 서비스 API', version: context.version });
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

    // 파일 목록 조회 API (페이지네이션 + 전체 조회 지원)
    router.get('/list', (req, res) => {
        // 요청 인자 (page와 limit이 없으면 기본값 설정)
        let page = parseInt(req.query.page) || 1;
        let limit = parseInt(req.query.limit) || 10;

        fs.readdir(uploadPath, (err, files) => {
            if (err) {
                return res.status(500).json({ error: '파일 목록을 조회할 수 없습니다.' });
            }

            // 파일의 전체 개수
            const totalFiles = files.length;

            // 파일명을 수정 날짜 기준으로 정렬 (최신 파일이 먼저 오도록)
            files = files
                .map(file => ({
                    name: file,
                    time: fs.statSync(path.join(uploadPath, file)).mtime.getTime()
                }))
                .sort((a, b) => b.time - a.time) // 최신 파일이 먼저 오도록 정렬
                .map(file => file.name);

            // page < 1이면 모든 파일 반환
            let paginatedFiles;
            if (page < 1) {
                paginatedFiles = files; // 모든 파일 반환
            } else {
                const startIndex = (page - 1) * limit;
                paginatedFiles = files.slice(startIndex, startIndex + limit);
            }

            // 응답 데이터 반환
            res.json({
                totalFiles: totalFiles, // 전체 파일 개수
                currentPage: page < 1 ? "ALL" : page, // 현재 페이지 (모두 가져올 때 "ALL" 표시)
                totalPages: page < 1 ? 1 : Math.ceil(totalFiles / limit), // 전체 페이지 개수
                files: paginatedFiles // 페이지별 파일 목록 (or 전체 목록)
            });
        });
    });


    //remove file
    router.get('/remove/:fileName', (req, res) => {
        const fileName = req.params.fileName;
        const filePath = path.join(uploadPath, fileName);

        fs.unlink(filePath, (err) => {
            if (err) {
                return res.status(500).json({ error: '파일을 삭제할 수 없습니다.' });
            }
            res.json({ message: '파일이 삭제되었습니다.' });
        });
    });

    //STT speech file(ASR) 인자로 파일을 넣어줌
    router.get('/stt/:fileName', (req, res) => {
        const fileName = req.params.fileName;
        const filePath = path.join(uploadPath, fileName);

        // STT 처리 로직


        // 여기서는 파일명을 그대로 텍스트로 반환 (테스트용)
        res.json({ text: fileName });
    });


    return router;
}
