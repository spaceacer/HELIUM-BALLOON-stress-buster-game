# scissor.py
import pygame
import math
from settings import WIDTH, HEIGHT, GRAVITY, SCISSOR_STEEL, SCISSOR_HANDLE

class Scissor:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.width = 90
        self.height = 40
        self.dragging = False
        self.velocity_y = 0
        
        # Blade Tip location relative to center (pointing right)
        self.tip_offset_x = 45
        self.tip_offset_y = 0

    @property
    def blade_tip(self):
        return (self.x + self.tip_offset_x, self.y + self.tip_offset_y)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check grab bounding zone around handle (left side of scissor)
            if math.hypot(event.pos[0] - self.x, event.pos[1] - self.y) < 40:
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def update(self):
        if self.dragging:
            mx, my = pygame.mouse.get_pos()
            self.x = float(mx)
            self.y = float(my)
            self.velocity_y = 0
        else:
            # Standard environmental gravity response
            self.velocity_y += GRAVITY
            self.y += self.velocity_y
            
            # Floor constraint boundary
            if self.y + 20 >= HEIGHT:
                self.y = HEIGHT - 20
                self.velocity_y = 0

    def draw(self, surface):
        # Draw Blades (Steel)
        pygame.draw.polygon(surface, SCISSOR_STEEL, [
            (int(self.x - 10), int(self.y - 5)),
            (int(self.x + self.tip_offset_x), int(self.y)),
            (int(self.x - 10), int(self.y + 5))
        ])
        
        # Draw Finger Rings (Handles)
        pygame.draw.circle(surface, SCISSOR_HANDLE, (int(self.x - 25), int(self.y - 12)), 14, 4)
        pygame.draw.circle(surface, SCISSOR_HANDLE, (int(self.x - 25), int(self.y + 12)), 14, 4)