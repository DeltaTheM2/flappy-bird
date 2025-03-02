import pygame, sys, random, cv2, mediapipe as mp, os, time, threading, lgpio
from picamera2 import Picamera2

# Disable audio to avoid PulseAudio/ALSA errors
os.environ["SDL_AUDIODRIVER"] = "dummy"

# --- Setup Asset Paths ---
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

# --- Screen Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600

# --- Initialize Mediapipe Hand Detection ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# --- Define Game Functions ---
def draw_floor():
    floor_y = SCREEN_HEIGHT - floor_surface.get_height()
    screen.blit(floor_surface, (floor_x_pos, floor_y))
    screen.blit(floor_surface, (floor_x_pos + floor_surface.get_width(), floor_y))

def create_pipe():
    random_pipe_pos = random.choice(pipe_height)
    pipe_gap = 150
    bottom_pipe = pipe_surface.get_rect(midtop=(SCREEN_WIDTH + 50, random_pipe_pos))
    top_pipe = pipe_surface.get_rect(midbottom=(SCREEN_WIDTH + 50, random_pipe_pos - pipe_gap))
    return bottom_pipe, top_pipe

def move_pipes(pipes):
    for pipe in pipes:
        pipe.centerx -= 5
    return pipes

def draw_pipes(pipes):
    for pipe in pipes:
        if pipe.bottom >= SCREEN_HEIGHT:
            screen.blit(pipe_surface, pipe)
        else:
            flip_pipe = pygame.transform.flip(pipe_surface, False, True)
            screen.blit(flip_pipe, pipe)

def remove_pipes(pipes):
    for pipe in pipes[:]:
        if pipe.centerx < -100:
            pipes.remove(pipe)
    return pipes

def check_collision(pipes):
    for pipe in pipes:
        if bird_rect.colliderect(pipe):
            return False
    floor_y = SCREEN_HEIGHT - floor_surface.get_height()
    if bird_rect.top <= 0 or bird_rect.bottom >= floor_y:
        return False
    return True

def rotate_bird(bird):
    new_bird = pygame.transform.rotozoom(bird, -bird_movement * 3, 1)
    return new_bird

def bird_animation():
    new_bird = bird_frames[bird_index]
    new_bird_rect = new_bird.get_rect(center=(100, bird_rect.centery))
    return new_bird, new_bird_rect

def score_display(game_state):
    if game_state == 'main_game':
        score_surface = game_font.render(str(int(score)), True, (255, 255, 255))
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(score_surface, score_rect)
    elif game_state == 'game_over':
        score_surface = game_font.render(f'Score: {int(score)}', True, (255, 255, 255))
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(score_surface, score_rect)
        high_score_surface = game_font.render(f'High score: {int(high_score)}', True, (255, 255, 255))
        high_score_rect = high_score_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        screen.blit(high_score_surface, high_score_rect)

def update_score(score, high_score):
    if score > high_score:
        high_score = score
    return high_score

def take_picture_countdown():
    for i in range(3, 0, -1):
        print(f"Taking picture in {i}...")
        time.sleep(1)
    filename = f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    picam2.capture_file(filename)
    print(f"Picture saved as {filename}")

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
game_font = pygame.font.Font(os.path.join(BASE_PATH, '04B_19.TTF'), 40)

# --- Game Variables ---
gravity = 0.5
bird_movement = 0
game_active = True
score = 0
high_score = 0

# --- Load Assets ---
bg_surface = pygame.image.load(os.path.join(BASE_PATH, 'assets', 'background-day.png')).convert()
bg_surface = pygame.transform.scale(bg_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))

floor_surface = pygame.image.load(os.path.join(BASE_PATH, 'assets', 'base.png')).convert()
floor_surface = pygame.transform.scale(floor_surface, (SCREEN_WIDTH, floor_surface.get_height()))
floor_x_pos = 0

bird_downflap = pygame.transform.scale2x(
    pygame.image.load(os.path.join(BASE_PATH, 'assets', 'bluebird-downflap.png')).convert_alpha())
bird_midflap = pygame.transform.scale2x(
    pygame.image.load(os.path.join(BASE_PATH, 'assets', 'bluebird-midflap.png')).convert_alpha())
bird_upflap = pygame.transform.scale2x(
    pygame.image.load(os.path.join(BASE_PATH, 'assets', 'bluebird-upflap.png')).convert_alpha())
bird_frames = [bird_downflap, bird_midflap, bird_upflap]
bird_index = 0
bird_surface = bird_frames[bird_index]
bird_rect = bird_surface.get_rect(center=(100, SCREEN_HEIGHT // 2))

pipe_surface = pygame.image.load(os.path.join(BASE_PATH, 'assets', 'pipe-green.png'))
pipe_surface = pygame.transform.scale2x(pipe_surface)
pipe_list = []
SPAWNPIPE = pygame.USEREVENT
pygame.time.set_timer(SPAWNPIPE, 2400)
pipe_height = [200, 250, 300]

game_over_surface = pygame.transform.scale2x(
    pygame.image.load(os.path.join(BASE_PATH, 'assets', 'message.png')).convert_alpha())
game_over_rect = game_over_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

# --- Setup Camera using Picamera2 ---
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(main={"format": "BGR888", "size": (640, 480)})
picam2.configure(camera_config)
picam2.start()

# --- Setup GPIO ---
BUTTON_PIN = 17
chip = lgpio.gpiochip_open(0)
lgpio.gpio_set_pull(chip, BUTTON_PIN, lgpio.PULL_UP)  # Set internal pull-up
button_last_state = 1  # Default HIGH due to pull-up

# --- Gesture State ---
flap_triggered = False
frame_count = 0
FLAP_ACTIVATE_THRESHOLD = 0.6
FLAP_DEACTIVATE_THRESHOLD = 0.5

# --- Main Game Loop ---
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            picam2.stop()
            cv2.destroyAllWindows()
            sys.exit()
        if event.type == SPAWNPIPE:
            print("Pipe Spawned!")
            pipe_list.extend(create_pipe())
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                print("Space pressed: Starting picture countdown.")
                threading.Thread(target=take_picture_countdown, daemon=True).start()

    # --- Check GPIO Button State ---
    try:
        button_state = lgpio.gpio_read(chip, BUTTON_PIN)
        print(f"Button state: {button_state}")  # Debug print
    except Exception as e:
        print("GPIO read error:", e)
        button_state = 1
    if button_last_state == 1 and button_state == 0:  # Falling edge (HIGH to LOW)
        print("Button pressed: Starting picture countdown.")
        threading.Thread(target=take_picture_countdown, daemon=True).start()
    button_last_state = button_state

    # --- Capture and Process Frame for Mediapipe ---
    frame = picam2.capture_array()
    if frame is not None:
        frame = cv2.flip(frame, 1)
        frame_resized = cv2.resize(frame, (320, 240))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        frame_count += 1
        if frame_count % 3 == 0:
            results = hands.process(frame_rgb)
            if results.multi_hand_landmarks:
                print(f"Detected {len(results.multi_hand_landmarks)} hands")
                if len(results.multi_hand_landmarks) >= 2:
                    wrist_y1 = results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.WRIST].y
                    wrist_y2 = results.multi_hand_landmarks[1].landmark[mp_hands.HandLandmark.WRIST].y
                    print(f"Wrist Y1: {wrist_y1:.3f}, Wrist Y2: {wrist_y2:.3f}")
                    if wrist_y1 < FLAP_ACTIVATE_THRESHOLD and wrist_y2 < FLAP_ACTIVATE_THRESHOLD and not flap_triggered:
                        flap_triggered = True
                        print("Flap triggered!")
                        if game_active:
                            bird_movement = 0
                            bird_movement -= 8
                        else:
                            game_active = True
                            pipe_list.clear()
                            bird_rect.center = (100, SCREEN_HEIGHT // 2)
                            bird_movement = 0
                            score = 0
                    elif wrist_y1 >= FLAP_DEACTIVATE_THRESHOLD or wrist_y2 >= FLAP_DEACTIVATE_THRESHOLD:
                        flap_triggered = False
                        print("Flap reset")
                else:
                    flap_triggered = False
                    print("Not enough hands detected")
            else:
                flap_triggered = False
                print("No hands detected")
    else:
        print("Failed to capture frame from Picamera2")

    # --- Game Rendering ---
    screen.blit(bg_surface, (0, 0))

    if game_active:
        bird_movement += gravity
        rotated_bird = rotate_bird(bird_surface)
        bird_rect.centery += bird_movement
        screen.blit(rotated_bird, bird_rect)
        game_active = check_collision(pipe_list)

        pipe_list = move_pipes(pipe_list)
        pipe_list = remove_pipes(pipe_list)
        draw_pipes(pipe_list)

        score += 0.01
        score_display('main_game')
    else:
        screen.blit(game_over_surface, game_over_rect)
        high_score = update_score(score, high_score)
        score_display('game_over')

    floor_x_pos -= 1
    draw_floor()
    if floor_x_pos <= -floor_surface.get_width():
        floor_x_pos = 0

    pygame.display.update()
    clock.tick(60)