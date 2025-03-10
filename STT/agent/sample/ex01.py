import pyaudio
import numpy as np
import pygame

# PyAudio 설정
CHUNK = 1024           # 한 번에 읽어올 샘플 수
FORMAT = pyaudio.paInt16  # 16비트 오디오
CHANNELS = 1           # 모노
RATE = 44100           # 샘플링 주파수

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

# pygame 초기화 및 화면 설정
pygame.init()
WIDTH, HEIGHT = 400, 300
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("마이크 테스트 프로그램")
clock = pygame.time.Clock()

# 폰트 객체 생성 (None 사용 시 기본 폰트 / SysFont 사용 가능)
font = pygame.font.Font(None, 36)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 마이크에서 오디오 데이터 읽기
    data = stream.read(CHUNK, exception_on_overflow=False)
    samples = np.frombuffer(data, dtype=np.int16)

    # 빈 배열일 경우를 처리하여 NaN 발생 방지
    if samples.size == 0:
        rms = 0
    else:
        rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
    
    max_val = 32768  # 16비트 최대값 (2^15)
    level = min(rms / max_val, 1.0)  # 0 ~ 1 사이 값

    bar_height = int(level * HEIGHT)

    # 화면 지우기
    screen.fill((0, 0, 0))

    # 막대 게이지 그리기
    bar_color = (0, 255, 0)
    bar_width = 50
    bar_x = (WIDTH - bar_width) // 2
    pygame.draw.rect(screen, bar_color, pygame.Rect(bar_x, HEIGHT - bar_height, bar_width, bar_height))

    # 텍스트로 레벨 표시
    # {:.2f}는 소수점 둘째 자리까지 표시
    text_surface = font.render(f"Level: {level:.2f}", True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()
