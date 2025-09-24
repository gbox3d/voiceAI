"""
filename: VadChecker.py
author: gbox3d
date : 2025-09-18
description:
범용 Silero VAD 기반 청크 처리기.

이 주석은 건드리지마시오.

"""

from __future__ import annotations
import torch
import numpy as np
from collections import deque
from typing import List, Tuple, Optional

class VadChecker:
    """
    범용 Silero VAD 기반 청크 처리기.
    - 입력: 16-bit PCM (mono) 바이트 청크들의 리스트
    - 출력: 완결된 발화 구간(bytes) 리스트 및(선택) 청크별 확률/라벨
    """
    def __init__(
        self,
        sample_rate: int = 16000,
        vad_threshold: float = 0.5,
        min_speech_ms: int = 150,     # 너무 짧은 발화는 무시(클릭음 등)
        min_silence_ms: int = 300,    # 이만큼 연속 침묵이면 발화 종료로 간주
        pre_buffer_ms: int = 200,     # 발화 시작부 보호(앞부분 붙여줌)
        device: str = "cpu",
        force_reload: bool = False
    ):
        """
        Args:
            sample_rate: 입력 청크의 샘플레이트(Hz). (예: 16000)
            vad_threshold: Silero 확률이 이 값 초과면 'speech'로 판정.
            min_speech_ms: 최종 segment 최소 길이(이하이면 폐기).
            min_silence_ms: 이 시간만큼 연속 침묵이면 segment 종료.
            pre_buffer_ms: 발화 시작 직전 버퍼링해서 머리 보호.
            device: 'cpu' or 'cuda'.
            force_reload: torch.hub 모델 강제 재로딩 여부.
        """
        self.sample_rate = int(sample_rate)
        self.vad_threshold = float(vad_threshold)
        self.min_speech_ms = int(min_speech_ms)
        self.min_silence_ms = int(min_silence_ms)
        self.pre_buffer_ms = int(pre_buffer_ms)
        self.device = device
        # Silero가 요구하는 프레임 샘플 수(32ms 고정): 16k→512, 8k→256
        self._frame_samples = 512 if self.sample_rate == 16000 else 256

        # Silero VAD 로드
        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=force_reload,
            onnx=False
        )
        self.vad_model.to(self.device)
        self.vad_model.eval()

        # 상태 변수
        self._speaking = False
        self._silence_ms = 0
        self._cur_seg = []               # 진행 중인 발화 segment (bytes 리스트)
        self._prebuf = deque()           # 프리버퍼 (bytes, ms 용량 제한 용)
        self._prebuf_ms_accum = 0        # 프리버퍼 누적 ms
        self._processed_samples = 0      # 지금까지 처리한 전체 샘플 수 (트랙 경과시간 기반)

        print(f"[VadChecker] initialized: sr={self.sample_rate}, th={self.vad_threshold}, "
              f"min_speech={self.min_speech_ms}ms, min_silence={self.min_silence_ms}ms, "
              f"pre_buffer={self.pre_buffer_ms}ms, device={self.device}")

    @staticmethod
    def _pcm16le_mono_bytes_to_tensor(chunk: bytes) -> torch.Tensor:
        """PCM16LE mono 바이트 → float32 텐서 [-1, 1]"""
        if not chunk:
            return torch.zeros(0, dtype=torch.float32)
        arr = np.frombuffer(chunk, dtype=np.int16)  # mono 가정
        # 정규화
        f32 = (arr.astype(np.float32) / 32768.0)
        return torch.from_numpy(f32)

    def _chunk_ms(self, chunk: bytes) -> float:
        """청크의 길이(ms) 계산 (PCM16 mono 가정)."""
        samples = len(chunk) // 2  # 2바이트 = int16
        return (samples / self.sample_rate) * 1000.0
    
    def _chunk_samples(self, chunk: bytes) -> int:
        return len(chunk) // 2

    def _silero_probs_from_tensor(self, x: torch.Tensor) -> list[float]:
        """
        임의 길이 텐서를 Silero frame size(512/256)로 잘라 프레임별 확률 리스트 반환.
        마지막 잔량은 0패딩.
        """
        n = x.numel()
        fs = self._frame_samples
        if n == 0:
            return [0.0]
        n_frames = (n + fs - 1) // fs
        probs: list[float] = []
        with torch.no_grad():
            for i in range(n_frames):
                start = i * fs
                end = min(start + fs, n)
                frame = x[start:end]
                if frame.numel() < fs:
                    pad = torch.zeros(fs - frame.numel(), dtype=frame.dtype, device=frame.device)
                    frame = torch.cat([frame, pad], dim=0)
                p = float(self.vad_model(frame, self.sample_rate).item())
                probs.append(p)
        return probs

    def _flush_segment_if_valid(self) -> Optional[tuple[bytes, int]]:
        """현재 진행 중 segment를 최소 길이 조건으로 검증 후 반환/폐기.
        Returns: Optional[(seg_bytes, seg_samples)]
        """
        if not self._cur_seg:
            return None
        
        # segment 길이(ms) 계산
        total_ms = sum(self._chunk_ms(c) for c in self._cur_seg)
        total_samples = sum(self._chunk_samples(c) for c in self._cur_seg)
        if total_ms >= self.min_speech_ms:
            seg = b"".join(self._cur_seg)
            self._cur_seg.clear()
            return seg, total_samples
        
        # 너무 짧으면 폐기
        self._cur_seg.clear()
        return None

    def _append_prebuffer_to_current(self):
        """프리버퍼 내용을 현재 segment 앞에 붙이고 비움."""
        while self._prebuf:
            self._cur_seg.append(self._prebuf.popleft())
        self._prebuf_ms_accum = 0

    def _silero_probs_from_tensor(self, x: torch.Tensor) -> list[float]:
        """
        임의 길이 텐서를 Silero가 요구하는 frame size(512/256)로 잘라
        프레임별 확률 리스트를 반환. 마지막 잔량은 0패딩.
        """
        n = x.numel()
        fs = self._frame_samples
        if n == 0:
            return [0.0]
        # 필요한 프레임 수
        n_frames = (n + fs - 1) // fs
        probs: list[float] = []
        with torch.no_grad():
            for i in range(n_frames):
                start = i * fs
                end = min(start + fs, n)
                frame = x[start:end]
                if frame.numel() < fs:
                    pad = torch.zeros(fs - frame.numel(), dtype=frame.dtype, device=frame.device)
                    frame = torch.cat([frame, pad], dim=0)
                p = float(self.vad_model(frame, self.sample_rate).item())
                probs.append(p)
        return probs

    def check_vad_chunks(
        self,
        chunks: List[bytes],
        return_details: bool = False,
        return_offsets: bool = True,
    ) -> Tuple[List[bytes], Optional[List[Tuple[float, bool]]], Optional[List[Tuple[int, int]]]]:
        """
        입력 청크들에 대해 VAD를 적용하고, 완결된 발화 구간(bytes)을 반환.
        필요 시 청크별 (확률, 라벨) 상세정보도 함께 반환.

        Args:
            chunks: PCM16 mono 바이트 청크 리스트
            return_details: True면 각 청크별 (prob, is_speech) 목록도 반환

        Returns:
            segments, details, offsets
            - segments: 완결된 발화 구간(bytes) 리스트
            - details: [(prob, is_speech), ...] 혹은 None (청크별)
            - offsets:  [(start_samples, end_samples), ...] 혹은 None  ※ 트랙 경과 기준
        """
        segments: List[bytes] = []
        details: List[Tuple[float, bool]] = [] if return_details else None
        offsets: List[Tuple[int, int]] = [] if return_offsets else None

        for chunk in chunks:
            if not chunk:
                if return_details:
                    details.append((0.0, False)) # 진행 시간은 빈 청크면 증가 없음
                continue

            # VAD 확률 계산
            x = self._pcm16le_mono_bytes_to_tensor(chunk).to(self.device)
            if x.numel() == 0:
                prob = 0.0
            else:
                frame_probs = self._silero_probs_from_tensor(x)
                # 집계 방식: '청크 내 어느 프레임이라도 말하면 말' → max 사용
                prob = max(frame_probs)


            is_speech = (prob > self.vad_threshold)
            if return_details:
                details.append((prob, is_speech))

            dur_ms = self._chunk_ms(chunk)
            samples_in_chunk = self._chunk_samples(chunk)

            if is_speech:
                # 발화 시작 전이었다면 프리버퍼를 머리에 붙임
                if not self._speaking:
                    self._speaking = True
                    self._append_prebuffer_to_current()
                # 현재 segment에 누적
                self._cur_seg.append(chunk)
                # 침묵 누적 초기화
                self._silence_ms = 0
            else:
                if self._speaking:
                    # 발화 중의 침묵 → 일정 시간 넘으면 종료
                    self._cur_seg.append(chunk)
                    self._silence_ms += dur_ms
                    if self._silence_ms >= self.min_silence_ms:
                        flushed = self._flush_segment_if_valid()
                        if flushed:
                            seg_bytes, seg_samples = flushed
                            # 이 시점의 세그먼트 종료 샘플 = (현재까지 처리한 샘플 + 이번 청크 샘플)
                            seg_end = self._processed_samples + samples_in_chunk
                            seg_start = seg_end - seg_samples
                            segments.append(seg_bytes)
                            if return_offsets:
                                offsets.append((seg_start, seg_end))
                        self._speaking = False
                        self._silence_ms = 0
                else:
                    # 발화 전이면 프리버퍼에 적재(용량 ms 제한)
                    self._prebuf.append(chunk)
                    self._prebuf_ms_accum += dur_ms
                    while self._prebuf and self._prebuf_ms_accum > self.pre_buffer_ms:
                        old = self._prebuf.popleft()
                        self._prebuf_ms_accum -= self._chunk_ms(old)
            # 루프 마지막에 '이번 청크 길이'만큼 트랙 경과 샘플 누적
            self._processed_samples += samples_in_chunk

        #return segments, details, offsets
        if return_details and details is not None:
            # 마지막 details 항목에 silence_ms 값도 묶어서 출력할 수 있게 tuple 확장
            # (prob, is_speech, silence_ms)
            new_details = []
            for (prob, is_speech) in details:
                new_details.append((prob, is_speech, self._silence_ms))
            return segments, new_details, offsets
        return segments, details, offsets

    def close(self):
        """현재 클래스는 외부 자원 없음(호출만 유지)."""
        pass


# -------- 사용 예시 --------
