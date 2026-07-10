# settings.py
WIDTH, HEIGHT = 1600, 1000

# Colors
BACKGROUND = (240, 248, 255)
TANK_BLUE = (30, 100, 180)
NOZZLE_GREY = (150, 150, 150)
BALLOON_COLOR = (255, 99, 71) 
STRING_COLOR = (50, 50, 50)
NODE_COLOR = (200, 200, 200)
OBJECT_BROWN = (139, 69, 19)
SCISSOR_STEEL = (180, 180, 190)
SCISSOR_HANDLE = (220, 40, 40)

# New Mass Object Colors
ANVIL_COLOR = (50, 50, 55)
CRATE_COLOR = (139, 90, 43)
FRIDGE_COLOR = (230, 230, 235)
WEIGHT_COLOR = (80, 80, 90)

# Physics Constants
CEILING_Y = 0
GRAVITY = 0.4             
LIFT_MULTIPLIER = 0.012   
MAX_BALLOON_RADIUS = 150 
DEFAULT_STRING_LENGTH = 112 
REEL_SPEED = 2

# Advanced Simulation Constants
AIR_DENSITY = 0.0006
DRAG_COEFF = 0.47        
VERLET_SEGMENTS = 4     # Slightly more segments for smoother curvature
VERLET_ITERATIONS = 15     # NEW: Increased from 3 to 8 for much higher structural stiffness

# Over-inflation Thresholds
DANGER_THRESHOLD = 0.85 

# Spring/Thread Physics
SPRING_STIFFNESS = 0.6   # Increased stiffness factor
SPRING_DAMPING = 0.08
DAMPING = 0.98
OBJECT_DAMPING = 0.95

# Bouquet Constants
MASTER_STRING_LENGTH = 75  
MAX_STRING_TENSION = 45.0  # Raised threshold to account for collective physics chain jerks

# Colors for Magic Hand
MAGIC_HAND_COLOR = (147, 112, 219)
MASTER_NODE_COLOR = (255, 165, 0)