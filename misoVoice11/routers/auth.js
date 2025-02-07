import jwt from 'jsonwebtoken';

export default function (context) {


    /**
     * JWT 인증 미들웨어
     * - 요청 헤더에서 Authorization 토큰을 추출하여 검증
     * - 유효한 경우 `req.user`에 디코딩된 사용자 정보를 저장
     * - 실패하면 401 Unauthorized 응답
     */

    const jwtAuth = (req, res, next) => {
        try {

            // 1) Authorization 헤더에서 Bearer 토큰 추출
            const token = req.headers.authorization?.split(' ')[1];

            if (!token) {
                console.log(`Authorization token is required. ip:${req.ip}`);

                return res.status(401).json({ message: 'Authorization token is required.' });
            }
            console.log('token:', token);

            //admin token check
            if (token === context.admin_key) {
                req.user = { username: 'admin' };
                console.log(`admi token is used. ip:${req.ip}`);
                return next();
            }

            // 2) JWT 검증
            const decoded = jwt.verify(token, process.env.JWT_SECRET);
            req.user = decoded; // 사용자 정보 저장 (예: { username: 'testuser' })

            // 3) 다음 미들웨어 또는 라우터로 이동
            next();
        } catch (error) {
            return res.status(401).json({ message: 'Invalid or expired token.' });
        }
    };

    return jwtAuth;
}