
# TTS App Server Protocol v1

본 문서는 TTS App Server와 통신하기 위한 **TCP 바이너리 프로토콜**을 정의합니다.

> **모든 다중 바이트 정수는 네트워크 바이트 순서(big-endian)** 로 인코딩됩니다.

---

## 1. 패킷 헤더 (32 bytes)

| 오프셋 | 크기 | 필드            | 설명 |
| ------:| ---: | --------------- | ---- |
| 0      | 4    | `CHECKCODE`     | ASCII `TTS1` 고정값 |
| 4      | 1    | `CODE`          | 요청 또는 응답 코드 |
| 5      | 1    | `FMT`           | 오디오 포맷 코드 (요청 시) |
| 6-7    | 2    | -- Reserved -- | 0 |
| 8      | 8    | `TIMESTAMP`     | UNIX epoch seconds |
| 16     | 4    | `PAYLOAD_SIZE`  | 바디 길이(byte) |
| 20-31  | 12   | -- Reserved -- | 0 |

---

## 2. 요청 코드

| 값  | 의미        | 바디 구조 |
| ----| ----------- | --------- |
| `0x01` | **TTS**  | `TEXT_LEN(4)` + UTF-8 문자열 |
| `0x63` | **PING** | (없음) |

`FMT` 필드는 TTS 요청에서만 사용됩니다.  
| 값 | 포맷 |
| ---|------|
| `0x01` | `wav` (PCM 16-bit, mono) |
| `0x02` | `mp3` (192 kbps, mono) |
| 그 외 | `mp3` (default) |

---

## 3. 응답 코드

| 값 | 의미 |
| --:| ---- |
| `0` | SUCCESS |
| `1` | ERR_CHECKCODE_MISMATCH |
| `2` | ERR_INVALID_DATA |
| `3` | ERR_INVALID_REQUEST |
| `4` | ERR_INVALID_PARAMETER |
| `5` | ERR_INVALID_FORMAT |
| `8` | ERR_UNKNOWN_CODE |
| `9` | ERR_EXCEPTION |
| `10`| ERR_TIMEOUT |

응답 헤더의 `CODE` 자리에 위 값을 세팅하고, `FMT` 필드는 무시합니다.

- **SUCCESS + PAYLOAD_SIZE>0** → 오디오 바이트 스트림
- **SUCCESS + PAYLOAD_SIZE=0** → Ping Pong
- **오류 코드** → 바디 없음

---

## 4. TTS 시퀀스

```text
Client                            Server
  │ ──Header(TTS)───────────────▶ │
  │ ──TEXT_LEN + UTF-8──────────▶ │
  │                               │ 음성 생성
  │ ◀────────Header(SUCCESS)──────│
  │ ◀────Audio Bytes (PAYLOAD)─── │

```
