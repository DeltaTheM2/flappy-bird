import pygame, sys, random, cv2, mediapipe as mp, os
from picamera2 import Picamera2  # Import Picamera2 for Raspberry Pi Camera support

# --- Setup Asset Paths ---
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

# --- Initialize Mediapipe Hand Detection ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# --- Define Game Functions ---
def draw_floor():
    screen.blit(floor_surface, (floor_x_pos, 900))
    screen.blit(floor_surface, (floor_x_pos + 576, 900))

def create_pipe():
    random_pipe_pos = random.choice(pipe_height)
    bottom_pipe = pipe_surface.get_rect(midtop=(700, random_pipe_pos))
    top_pipe = pipe_surface.get_rect(midbottom=(700, random_pipe_pos - 300))
    return bottom_pipe, top_pipe

def move_pipes(pipes):
    for pipe in pipes:
        pipe.centerx -= 5
    return pipes

def draw_pipes(pipes):
    for pipe in pipes:
        if pipe.bottom >= 1024:
            screen.blit(pipe_surface, pipe)
        else:
            flip_pipe = pygame.transform.flip(pipe_surface, False, True)
            screen.blit(flip_pipe, pipe)

def remove_pipes(pipes):
    for pipe in pipes[:]:
        if pipe.centerx < -100:  # Remove pipes that have moved off-screen
            pipes.remove(pipe)
    return pipes

def check_collision(pipes):
    for pipe in pipes:
        if bird_rect.colliderect(pipe):
            return False
    if bird_rect.top <= -100 or bird_rect.bottom >= 900:
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
        score_rect = score_surface.get_rect(center=(288, 100))
        screen.blit(score_surface, score_rect)
    elif game_state == 'game_over':
        score_surface = game_font.render(f'Score: {int(score)}', True, (255, 255, 255))
        score_rect = score_surface.get_rect(center=(288, 100))
        screen.blit(score_surface, score_rect)

        high_score_surface = game_font.render(f'High score: {int(high_score)}', True, (255, 255, 255))
        high_score_rect = high_score_surface.get_rect(center=(288, 850))
        screen.blit(high_score_surface, high_score_rect)

def update_score(score, high_score):
    if score > high_score:
        high_score = score
    return high_score

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode((800, 600))
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
bg_surface = pygame.transform.scale2x(bg_surface)

floor_surface = pygame.image.load(os.path.join(BASE_PATH, 'assets', 'base.png')).convert()
floor_surface = pygame.transform.scale2x(floor_surface)
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
bird_rect = bird_surface.get_rect(center=(350, 300))

pipe_surface = pygame.image.load(os.path.join(BASE_PATH, 'assets', 'pipe-green.png'))
pipe_surface = pygame.transform.scale2x(pipe_surface)
pipe_list = []
SPAWNPIPE = pygame.USEREVENT
pygame.time.set_timer(SPAWNPIPE, 2400)
pipe_height = [150, 250, 350]

game_over_surface = pygame.transform.scale2x(
    pygame.image.load(os.path.join(BASE_PATH, 'assets', 'message.png')).convert_alpha())
game_over_rect = game_over_surface.get_rect(center=(288, 512))

flap_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, 'sound', 'sfx_wing.wav'))
death_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, 'sound', 'sfx_hit.wav'))
score_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, 'sound', 'sfx_point.wav'))
score_sound_countdown = 100

# --- Setup Camera using Picamera2 ---
picam2 = Picamera2()
# Configure the camera to output BGR frames (for OpenCV compatibility) at 640x480.
camera_config = picam2.create_preview_configuration(main={"format": "BGR888", "size": (640, 480)})
picam2.configure(camera_config)
picam2.start()

# --- Gesture State ---
flap_triggered = False
frame_count = 0  # Counter to control how often Mediapipe processes a frame

# --- Main Game Loop ---
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            picam2.stop()
            cv2.destroyAllWindows()
            sys.exit()

        # Pipe spawning event
        if event.type == SPAWNPIPE:
            print("Pipe Spawned!")
            pipe_list.extend(create_pipe())

    # --- Capture Frame from Picamera2 ---
    frame = picam2.capture_array()
    if frame is not None:
        # Flip horizontally for a mirror view.
        frame = cv2.flip(frame, 1)
        # Resize to a smaller resolution for faster processing.
        frame_resized = cv2.resize(frame, (320, 240))
        # Convert from BGR (camera format) to RGB for Mediapipe.
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        # Process Mediapipe every 3rd frame to reduce CPU load.
        frame_count += 1
        if frame_count % 3 == 0:
            results = hands.process(frame_rgb)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    wrist_y = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y
                    print(f"Wrist Y: {wrist_y}")  # Debug output

                    # Trigger a flap if the wrist is raised.
                    if wrist_y < 0.5 and not flap_triggered:
                        flap_triggered = True
                        if game_active:
                            bird_movement = 0
                            bird_movement -= 8
                            flap_sound.play()
                        else:  # Restart game if it's over.
                            game_active = True
                            pipe_list.clear()
                            bird_rect.center = (100, 512)
                            bird_movement = 0
                            score = 0
                    elif wrist_y >= 0.4:
                        flap_triggered = False
    else:
        print("Failed to capture frame from Picamera2.")

    # --- Game Rendering ---
    screen.blit(bg_surface, (0, 0))

    if game_active:
        # Bird motion and rotation
        bird_movement += gravity
        rotated_bird = rotate_bird(bird_surface)
        bird_rect.centery += bird_movement
        screen.blit(rotated_bird, bird_rect)
        game_active = check_collision(pipe_list)

        # Pipe movement and drawing
        pipe_list = move_pipes(pipe_list)
        pipe_list = remove_pipes(pipe_list)
        draw_pipes(pipe_list)

        # Update score
        score += 0.01
        score_display('main_game')
        score_sound_countdown -= 1
        if score_sound_countdown <= 0:
            score_sound.play()
            score_sound_countdown = 100
    else:
        screen.blit(game_over_surface, game_over_rect)
        high_score = update_score(score, high_score)
        score_display('game_over')

    # Floor movement
    floor_x_pos -= 1
    draw_floor()
    if floor_x_pos <= -576:
        floor_x_pos = 0

    pygame.display.update()
    clock.tick(60)  # Limit frame rate to 60 FPS
