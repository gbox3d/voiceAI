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

import net from 'net';

import AuthSetup from './auth.js';




export default function (context) {

    const router = express.Router();
    const authMiddleware = AuthSetup(context);

    const asrServer = {
        host : process.env.ASR_HOST || 'localhost',
        port : process.env.ASR_PORT || 2500,
        checkcode : process.env.ASR_CHECKCODE || 20250122
    }

    function stt(audioData,formatCode,res) {

        // ASR 서버에 전달할 값들 (체크코드, 요청 코드 등)
        const checkcode = asrServer.checkcode; // 예시
        const requestCode = 0x01; // STT 요청 코드
    
        // 헤더 구성: 8바이트 (checkcode 4바이트, requestCode 4바이트)
        const headerBuffer = Buffer.alloc(8);
        headerBuffer.writeInt32BE(checkcode, 0);
        headerBuffer.writeInt32BE(requestCode, 4);
    
        // 포맷 코드: 1바이트
        const formatBuffer = Buffer.alloc(1);
        formatBuffer.writeUInt8(formatCode, 0);
    
        // 오디오 데이터 길이: 4바이트 정수 (빅엔디안)
        const sizeBuffer = Buffer.alloc(4);
        sizeBuffer.writeInt32BE(audioData.length, 0);
    
        // Python ASR 서버 (예: localhost:2500)에 연결하여 전송
        const client = new net.Socket();
        let dataBuffers = [];
    
        client.connect(asrServer.port, asrServer.host, () => {
            console.log('[INFO] Python ASR 서버에 연결됨.');
            // 순서대로 헤더, 포맷, 크기, 파일 데이터를 전송
            client.write(headerBuffer);
            client.write(formatBuffer);
            client.write(sizeBuffer);
            client.write(audioData);
        });
    
        client.on('data', (data) => {
            dataBuffers.push(data);
        });
    
        client.on('end', () => {
            const fullBuffer = Buffer.concat(dataBuffers);
            // 응답 데이터 파싱
            // 응답 구조: [checkcode (4바이트)][requestCode (4바이트)][status (1바이트)]
            // status가 0이면 성공, 그 다음 4바이트로 텍스트 길이, 그 후 텍스트 데이터가 옴.
            const respCheckcode = fullBuffer.readInt32BE(0);
            const respRequestCode = fullBuffer.readInt32BE(4);
            const status = fullBuffer.readUInt8(8);

            console.log(`[INFO] ASR 서버 응답: checkcode=${respCheckcode}, requestCode=${respRequestCode}, status=${status}`);
    
            if (status !== 0) {
                console.error(`[ERROR] STT 변환 실패, status: ${status}`);
                return res.status(500).json({ error: 'STT 변환 중 오류가 발생했습니다.', status });
            }
            // 텍스트 길이 (4바이트)
            const textLength = fullBuffer.readInt32BE(9);
            // 텍스트 데이터: 13번째 바이트부터 textLength 바이트
            const text = fullBuffer.subarray(13, 13 + textLength).toString('utf8');
    
            console.log(`[INFO] 전사 결과: ${text}`);
            res.json({ text , status });
        });
    
        client.on('error', (err) => {
            console.error('[ERROR] Python ASR 서버 연결 오류:', err.message);
            res.status(500).json({ error: 'Python ASR 서버 연결 오류', details: err.message });
        });
    }

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

    // STT API: 파일명을 받아 해당 파일을 열어 Python ASR 서버로 전송 후 결과 반환
    router.get('/recognize/:fileName', async (req, res) => {
        const fileName = req.params.fileName;
        const filePath = path.join(uploadPath, fileName);

        try {
            // 파일 읽기 (버퍼로)
            const audioData = await fs.readFile(filePath);

            // 파일 확장자에 따라 포맷 코드 지정 (예: wav:1, mp3:2, webm:3)
            const ext = path.extname(fileName).toLowerCase();
            let formatCode = 0;
            if (ext === '.wav') formatCode = 1;
            else if (ext === '.mp3') formatCode = 2;
            else if (ext === '.webm') formatCode = 3;
            else {
                return res.status(400).json({ error: '지원하지 않는 파일 포맷입니다.' });
            }

            // STT 요청
            stt(audioData, formatCode, res);


        } catch (err) {
            console.error('[ERROR] 파일 읽기 또는 처리 중 오류:', err.message);
            res.status(500).json({ error: '파일 읽기 또는 처리 중 오류', details: err.message });
        }
    });


    return router;
}
