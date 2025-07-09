from flask import Flask, request, Response
import requests
import ssl
from flask_cors import CORS
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
CORS(app)  # 모든 라우트에 CORS 활성화

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'])
def proxy(path):
    # 루트 경로 특별 처리
    if path == '':
        url = "http://localhost:11434/api/version"
        print("루트 경로 요청, /api/version으로 리다이렉트")
    else:
        url = f"http://localhost:11434/{path}"
    
    print(f"요청 URL: {url}")
    print(f"요청 메서드: {request.method}")
    
    # 요청 메서드가 OPTIONS인 경우 (preflight 요청)
    if request.method == 'OPTIONS':
        response = Response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
    
    # 모든 헤더 전달
    # 단순화된 헤더 사용
    headers = {}
    if 'Content-Type' in request.headers:
        headers['Content-Type'] = request.headers['Content-Type']
    
    
    # 요청 메서드에 따른 처리
    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        stream=True
    )
    
    # 응답 헤더 처리
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for name, value in resp.raw.headers.items()
               if name.lower() not in excluded_headers]
    
    # CORS 헤더 추가
    response = Response(resp.content, resp.status_code, headers)
    response.headers.add('Access-Control-Allow-Origin', '*')
    
    return response

if __name__ == '__main__':
    # .env 파일에서 SSL 설정 가져오기
    ssl_enabled = os.getenv('SSL', 'False').lower() == 'true'
    ssl_cert = os.getenv('SSL_CERT')
    ssl_key = os.getenv('SSL_KEY')
    ssl_ca = os.getenv('SSL_CA')
    port = int(os.getenv('PORT', '22244'))
    
    print(f"SSL 활성화: {ssl_enabled}")
    print(f"포트: {port}")
    
    if ssl_enabled and ssl_cert and ssl_key:
        # SSL 컨텍스트 설정
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(ssl_cert, ssl_key)
        
        # CA 인증서가 있으면 로드
        if ssl_ca:
            context.load_verify_locations(ssl_ca)
        
        print(f"SSL 인증서: {ssl_cert}")
        print(f"SSL 키: {ssl_key}")
        if ssl_ca:
            print(f"SSL CA: {ssl_ca}")
        
        # HTTPS로 실행
        app.run(host='0.0.0.0', port=port, ssl_context=context, debug=False)
    else:
        # HTTP로 실행
        print("SSL이 비활성화되었거나 인증서/키가 설정되지 않았습니다. HTTP로 실행합니다.")
        app.run(host='0.0.0.0', port=port, debug=False)