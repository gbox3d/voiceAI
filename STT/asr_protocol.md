# ASR 서버 통신 프로토콜

이 문서는 비동기 STT 서버(`AsrServer`)와 클라이언트 간의 TCP 통신 프로토콜 사양을 설명합니다. 프로그래머가 구현 시 참조할 수 있도록 상세히 기술하였습니다.

---

## 1. 개요

- **전송 방식**: TCP 소켓  
- **바이트 순서**: Big-endian (`network byte order`)  
- **구조체 사용**: Python `struct` 모듈의 `"!"` 포맷 지정자  

### 환경 설정

- 호스트: `ASR_HOST` (기본: `localhost`)  
- 포트: `ASR_PORT` (기본: `26070` 또는 코드 내 설정)  
- `checkcode`: 인증 코드 (기본: `20250122`)  
- `timeout`: I/O 대기 시간 (초 단위)  

---

## 2. 메시지 프레임워크

모든 요청(request)과 응답(response)은 다음과 같은 공통 헤더를 가집니다.

```c
// 공통 헤더 (총 9바이트 요청, 9바이트 + 가변 페이로드 응답)
struct {
    int32_t checkcode;     // 인증 코드
    int32_t request_code;  // 요청 코드
    uint8_t status_code;   // (응답 시) 상태 코드
};
```

- 요청(request): `checkcode(4B)` + `request_code(4B)`  
- 응답(response): `checkcode(4B)` + `request_code(4B)` + `status_code(1B)`  
  - STT 요청인 경우, 추가로 `payload_length(4B)` + `payload`가 뒤따름  

---

## 3. 요청 코드(Request Codes)

| 코드 (int) | 이름    | 설명             |
|-----------:|---------|------------------|
| 99         | PING    | 연결 확인용 핑  |
| 0x01       | STT     | 오디오 → 텍스트 |

### 3.1 PING 요청 (99)

- **클라이언트**:  
  - 헤더: `checkcode`, `request_code=99`  
- **서버**:  
  - 응답 헤더: `checkcode`, `request_code=99`, `status_code=0` (성공)  
  - 페이로드 없음  

```python
# Python 예시
# 요청
sock.send(struct.pack('!ii', checkcode, 99))
# 응답
data = sock.recv(9)
checkcode_resp, code_resp, status = struct.unpack('!iiB', data)
```

### 3.2 STT 요청 (0x01)

1. **헤더 전송**: `checkcode` + `request_code=1`  
2. **오디오 포맷 코드**: 1바이트  
3. **오디오 데이터 길이**: 4바이트 (int32)  
4. **오디오 바이트**: 지정된 길이만큼  

```c
// 헤더
pack('!ii', checkcode, 1);
// 포맷 코드 (uint8_t)
pack('!B', format_code);
// 데이터 크기 (int32)
pack('!i', audio_size);
// 실제 audio bytes
send(audio_bytes);
```

#### 3.2.1 오디오 포맷 매핑

| 포맷 코드 | 형식  | 설명          |
|----------:|-------|---------------|
| 1         | wav   | WAV (PCM)     |
| 2         | mp3   | MP3           |
| 3         | webm  | WEBM          |
| 4         | mp4   | MP4 (AAC 등)  |

---

## 4. 응답 구조(Response Format)

STT 요청(`request_code=1`)에 대한 응답은 다음과 같습니다.

1. **응답 헤더**: `checkcode(4B)` + `request_code(4B)` + `status_code(1B)`  
2. **결과 길이**: `payload_length(4B)` (int32, 텍스트 바이트 수)  
3. **결과 텍스트**: UTF-8 인코딩된 바이트  

```c
// status_code != 0이면 payload 없음
int32_t checkcode;
int32_t request_code;
uint8_t status_code;
int32_t payload_length;
char payload[payload_length];
```

예시 (Python):
```python
# 응답 읽기
header = sock.recv(9)
checkcode_resp, code_resp, status = struct.unpack('!iiB', header)
if status == 0:  # SUCCESS
    length_bytes = sock.recv(4)
    length = struct.unpack('!i', length_bytes)[0]
    text = sock.recv(length).decode('utf-8')
else:
    # 오류 처리
```

---

## 5. 상태 코드(Status Codes)

| 값  | 이름                     | 설명                                      |
|-----|--------------------------|-------------------------------------------|
| 0   | SUCCESS                  | 정상 처리                                 |
| 1   | ERR_CHECKCODE_MISMATCH   | 인증 코드 불일치                          |
| 2   | ERR_INVALID_DATA         | 데이터 수신 오류 또는 크기 불일치         |
| 3   | ERR_INVALID_REQUEST      | 잘못된 요청 (모델 미초기화 등)            |
| 4   | ERR_INVALID_PARAMETER    | 파라미터 오류                             |
| 5   | ERR_INVALID_FORMAT       | 지원하지 않는 오디오 포맷                |
| 8   | ERR_UNKNOWN_CODE         | 알 수 없는 요청 코드                     |
| 9   | ERR_EXCEPTION            | 서버 내부 예외                            |
| 10  | ERR_TIMEOUT              | I/O 타임아웃                              |

---

## 6. 구현 예제

### C# 클라이언트 예시 (STT 요청)
```csharp
using System;
using System.Net.Sockets;
using System.Text;

... 

// 1) 연결
var client = new TcpClient(host, port);
var stream = client.GetStream();
// 2) 헤더
var header = BitConverter.GetBytes(IPAddress.HostToNetworkOrder(checkcode))
            .Concat(BitConverter.GetBytes(IPAddress.HostToNetworkOrder(1))).ToArray();
stream.Write(header, 0, header.Length);
// 3) 포맷 코드
stream.Write(new byte[]{ formatCode }, 0, 1);
// 4) 길이
var sizeBytes = BitConverter.GetBytes(IPAddress.HostToNetworkOrder(audioBytes.Length));
stream.Write(sizeBytes, 0, 4);
// 5) 오디오
stream.Write(audioBytes, 0, audioBytes.Length);

// 6) 응답 처리
var respHeader = new byte[9];
stream.Read(respHeader, 0, 9);
// (이하 동일하게 언팩 및 처리)
```

---

## 7. 주의사항

- `checkcode`는 클라이언트/서버 간 사전 공유되어야 합니다.  
- 네트워크 장애 대비 재시도 로직 권장.  
- 대용량 오디오 전송 시 스트리밍 또는 청크 방식 고려 가능.  
