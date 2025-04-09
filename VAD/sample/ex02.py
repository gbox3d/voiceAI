import pygame
import sys
import os

# 한글 입력을 위한 SDL 환경 변수 설정
os.environ['SDL_IME_SHOW_UI'] = '1'  # IME UI 표시
os.environ['SDL_IME_ENABLE_POLLING'] = '1'  # IME 폴링 활성화

# Pygame 초기화 (환경 변수 설정 후에 초기화해야 함)
pygame.init()
pygame.font.init()

# 화면 설정
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("레트로 어드밴처 - 한글 입력 (수정)")

# 색상 정의
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
RED = (255, 0, 0)

# 한글 폰트 설정 (시스템에 설치된 폰트 사용)
font_path = None

# 윈도우 폰트 경로 확인
windows_fonts = [
    "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
    "C:/Windows/Fonts/gulim.ttc",    # 굴림
    "C:/Windows/Fonts/batang.ttc",   # 바탕
    "C:/Windows/Fonts/dotum.ttc"     # 돋움
]

for path in windows_fonts:
    if os.path.exists(path):
        font_path = path
        break

if font_path:
    print(f"한글 폰트를 찾았습니다: {font_path}")
    font = pygame.font.Font(font_path, 20)
else:
    print("한글 폰트를 찾을 수 없습니다. 기본 폰트로 대체합니다.")
    font = pygame.font.Font(None, 20)

class TextBox:
    def __init__(self, x, y, width, height, font=None, placeholder="여기에 입력하세요..."):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = GRAY
        self.font = font
        self.active = False
        self.text = ""
        self.ime_text = ""  # IME 조합 중인 텍스트
        self.placeholder = placeholder
        self.rendered_text = font.render(placeholder, True, (150, 150, 150))
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_position = 0
        self.submitted_text = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.color = WHITE
                # IME 활성화 위치 설정
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(self.rect)
            else:
                self.active = False
                self.color = GRAY
                pygame.key.stop_text_input()
                
        # 한글 입력을 위한 TEXTINPUT 이벤트 처리
        if event.type == pygame.TEXTINPUT and self.active:
            if event.text:  # 텍스트가 비어있지 않을 때만 처리
                print(f"입력된 텍스트: {event.text!r}")  # 디버깅용
                self.text = self.text[:self.cursor_position] + event.text + self.text[self.cursor_position:]
                self.cursor_position += len(event.text)
                self.ime_text = ""  # 조합 텍스트 초기화
        
        # IME 조합 중인 텍스트 처리 (윈도우 10 한글 입력)
        if event.type == pygame.TEXTEDITING and self.active:
            self.ime_text = event.text
            print(f"IME 조합중: {self.ime_text!r}")  # 디버깅용
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                if self.cursor_position > 0:
                    self.text = self.text[:self.cursor_position-1] + self.text[self.cursor_position:]
                    self.cursor_position -= 1
            elif event.key == pygame.K_LEFT:
                self.cursor_position = max(0, self.cursor_position - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_position = min(len(self.text), self.cursor_position + 1)
            elif event.key == pygame.K_RETURN:
                if self.text:
                    print(f"입력된 한글 (엔터): {self.text}")
                    self.submitted_text = self.text
                    self.text = ""
                    self.cursor_position = 0
            
            # 텍스트 렌더링 업데이트
            self.update_rendered_text()

    def update_rendered_text(self):
        # 텍스트와 IME 조합 텍스트를 합쳐서 렌더링
        display_text = self.text[:self.cursor_position] + self.ime_text + self.text[self.cursor_position:]
        if display_text:
            self.rendered_text = self.font.render(display_text, True, BLACK)
        else:
            self.rendered_text = self.font.render(self.placeholder, True, (150, 150, 150))

    def update(self):
        # 커서 깜빡임 업데이트
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

    def draw(self, screen):
        # 텍스트 박스 그리기
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        # 텍스트 표시
        if self.text or self.ime_text:
            screen.blit(self.rendered_text, (self.rect.x + 5, self.rect.y + 5))
        else:
            screen.blit(self.rendered_text, (self.rect.x + 5, self.rect.y + 5))
            
        # 활성화 상태에서 커서 표시
        if self.active and self.cursor_visible:
            # IME 조합 텍스트를 고려한 커서 위치 계산
            cursor_text = self.text[:self.cursor_position] + self.ime_text
            cursor_x = self.rect.x + 5 + self.font.size(cursor_text)[0]
                
            pygame.draw.line(screen, BLACK, 
                           (cursor_x, self.rect.y + 5),
                           (cursor_x, self.rect.y + self.rect.height - 5), 2)

# 디버그 정보 표시 함수
def draw_debug_info(screen, font, textbox):
    debug_info = [
        f"텍스트: '{textbox.text}'",
        f"IME 텍스트: '{textbox.ime_text}'",
        f"커서 위치: {textbox.cursor_position}",
        f"활성 상태: {textbox.active}"
    ]
    
    for i, info in enumerate(debug_info):
        debug_text = font.render(info, True, WHITE)
        screen.blit(debug_text, (10, 10 + i * 25))

# 메인 루프
def main():
    clock = pygame.time.Clock()
    textbox = TextBox(150, 250, 500, 40, font, "한글을 입력하세요...")
    running = True
    debug_mode = True  # 디버깅 정보 표시 모드
    
    # 배경 이미지
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((50, 50, 80))
    for i in range(0, WIDTH, 20):
        pygame.draw.line(background, (60, 60, 100), (i, 0), (i, HEIGHT))
    for i in range(0, HEIGHT, 20):
        pygame.draw.line(background, (60, 60, 100), (0, i), (WIDTH, i))
    
    # 콘솔 출력 안내 메시지
    print("=== 한글 입력 테스트 (수정) ===")
    print("텍스트를 입력하고 엔터키를 누르면 콘솔에 출력됩니다.")
    print("================================")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # F1키를 누르면 디버그 모드 토글
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                debug_mode = not debug_mode
                print(f"디버그 모드: {'켜짐' if debug_mode else '꺼짐'}")
            
            textbox.handle_event(event)
            
        textbox.update()
        textbox.update_rendered_text()  # IME 텍스트 업데이트를 위해 매 프레임마다 호출
        
        # 화면 그리기
        screen.blit(background, (0, 0))
        
        # 제목 표시
        title = font.render("레트로 어드밴처 - 한글 입력 테스트", True, (255, 220, 0))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        
        # 텍스트 박스 그리기
        textbox.draw(screen)
        
        # 제출된 텍스트 표시
        if textbox.submitted_text:
            preview = font.render(f"마지막 입력: {textbox.submitted_text}", True, WHITE)
            screen.blit(preview, (WIDTH//2 - preview.get_width()//2, 350))
        
        # 사용 안내 표시
        instruction = font.render("텍스트를 입력하고 엔터키를 누르세요 (F1: 디버그 모드)", True, (200, 200, 200))
        screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, 450))
        
        # 디버그 정보 표시
        if debug_mode:
            draw_debug_info(screen, font, textbox)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()