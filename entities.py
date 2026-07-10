# entities.py
import pygame
import math
from settings import WIDTH, HEIGHT, GRAVITY, OBJECT_DAMPING, CEILING_Y, TANK_BLUE, NOZZLE_GREY, OBJECT_BROWN, FRIDGE_COLOR

pygame.font.init()
UI_FONT = pygame.font.SysFont("Arial", 16, bold=True)
MASS_FONT = pygame.font.SysFont("Arial", 14)

class HeliumTank:
    def __init__(self):
        self.x = 250 
        self.y = HEIGHT - 200
        self.width = 80
        self.height = 200
        self.nozzle_x = self.x + self.width
        self.nozzle_y = self.y + 30
        self.top_tie_x = self.nozzle_x - 10
        self.top_tie_y = self.nozzle_y + 15
        
    def draw(self, surface):
        pygame.draw.rect(surface, TANK_BLUE, (self.x, self.y, self.width, self.height), border_radius=10)
        pygame.draw.rect(surface, NOZZLE_GREY, (self.nozzle_x, self.nozzle_y, 35, 12))

class Table:
    def __init__(self):
        self.rect = pygame.Rect(30, HEIGHT - 100, 150, 20)
        self.leg1 = pygame.Rect(45, HEIGHT - 80, 15, 80)
        self.leg2 = pygame.Rect(150, HEIGHT - 80, 15, 80)
        
    def draw(self, surface):
        pygame.draw.rect(surface, OBJECT_BROWN, self.leg1)
        pygame.draw.rect(surface, OBJECT_BROWN, self.leg2)
        pygame.draw.rect(surface, OBJECT_BROWN, self.rect, border_radius=3)

class RoomObject:
    def __init__(self, x, y, width, height, mass, color, name=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.exact_x = float(x)
        self.exact_y = float(y) 
        self.width = width
        self.height = height
        self.mass = mass
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        
        # Rotational Physics for Torque
        self.angle = 0.0
        self.angular_velocity = 0.0
        
        self.attached_balloons = []
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Pre-render the object's visual surface for smooth hardware rotation
        self.base_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.base_surface, color, (0, 0, width, height), border_radius=5)
        
        text_color = (0, 0, 0) if color == FRIDGE_COLOR else (255, 255, 255)
        if name:
            name_lbl = UI_FONT.render(name, True, text_color)
            self.base_surface.blit(name_lbl, (5, 5))
        mass_lbl = MASS_FONT.render(f"{self.mass} kg", True, text_color)
        self.base_surface.blit(mass_lbl, (5, 25))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.drag_offset_x = self.rect.x - event.pos[0]
                self.drag_offset_y = self.rect.y - event.pos[1]
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        
    def update(self):
        if self.dragging:
            mx, my = pygame.mouse.get_pos()
            self.exact_x = float(mx + self.drag_offset_x)
            self.exact_y = float(my + self.drag_offset_y)
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.angular_velocity = 0.0
            self.angle *= 0.8  # Center orientation when grabbed
            self.rect.x = int(self.exact_x)
            self.rect.y = int(self.exact_y)
        else:
            self.velocity_y += GRAVITY
            
            # --- NEW: Calculate Rotational Torque from Multi-Point Attachments ---
            torque = 0.0
            total_lift = 0.0
            
            # --- FIX: Iterate over a copy [:] to prevent mid-loop mutation crashes ---
            for b in self.attached_balloons[:]:
                if not getattr(b, 'popped', False):
                    lift = b.get_lift()
                    total_lift += lift
                    # Find horizontal distance from the center of mass
                    local_x = b.master_anchor_offset_x - (self.width / 2)
                    # Downward torque is counter-acted by upward lift
                    torque -= local_x * lift * 0.015
            
            self.angular_velocity += torque / self.mass
            self.angular_velocity *= 0.88 # Angular damping
            self.angle += self.angular_velocity
            
            # Clamp angle to maintain AABB bounding box collision stability
            self.angle = max(-35.0, min(35.0, self.angle))
            
            self.velocity_y -= total_lift / self.mass
            
            self.velocity_y *= OBJECT_DAMPING
            self.velocity_x *= OBJECT_DAMPING
            
            self.exact_x += self.velocity_x
            self.exact_y += self.velocity_y
            self.rect.x = int(self.exact_x)
            self.rect.y = int(self.exact_y)
            
            if self.rect.bottom >= HEIGHT:
                self.rect.bottom = HEIGHT
                self.exact_y = float(self.rect.y)
                self.velocity_y = 0.0
                self.velocity_x *= 0.8 
                
            if self.rect.top <= CEILING_Y:
                self.rect.top = CEILING_Y
                self.exact_y = float(self.rect.top)
                if self.velocity_y < 0:
                    self.velocity_y = 0.0
                    
            if self.rect.left <= 0:
                self.rect.left = 0
                self.exact_x = float(self.rect.x)
                self.velocity_x *= -0.5
            elif self.rect.right >= WIDTH:
                self.rect.right = WIDTH
                self.exact_x = float(self.rect.x)
                self.velocity_x *= -0.5

    def draw(self, surface):
        if abs(self.angle) > 0.1:
            rotated_surf = pygame.transform.rotate(self.base_surface, self.angle)
            new_rect = rotated_surf.get_rect(center=self.rect.center)
            surface.blit(rotated_surf, new_rect.topleft)
        else:
            surface.blit(self.base_surface, self.rect.topleft)


def unified_physics_sweep(objects, balloons, iterations=4):
    """A unified physical interaction pass serving all bodies in the scene."""
    # 1. Object vs Object Resolution (Sweep & Prune AABB Base)
    for _ in range(iterations):
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                a, b = objects[i], objects[j]
                if not a.rect.colliderect(b.rect): continue

                dx = a.rect.centerx - b.rect.centerx
                dy = a.rect.centery - b.rect.centery
                overlap_x = (a.rect.width + b.rect.width) / 2 - abs(dx)
                overlap_y = (a.rect.height + b.rect.height) / 2 - abs(dy)

                if overlap_x <= 0 or overlap_y <= 0: continue

                inv_a = 0.0 if a.dragging else 1.0 / a.mass
                inv_b = 0.0 if b.dragging else 1.0 / b.mass
                total_inv = inv_a + inv_b
                if total_inv == 0: continue

                if overlap_x < overlap_y:
                    push_a, push_b = overlap_x * (inv_a/total_inv), overlap_x * (inv_b/total_inv)
                    if dx < 0:
                        a.exact_x -= push_a
                        b.exact_x += push_b
                    else:
                        a.exact_x += push_a
                        b.exact_x -= push_b
                    a.velocity_x *= 0.3
                    b.velocity_x *= 0.3
                else:
                    push_a, push_b = overlap_y * (inv_a/total_inv), overlap_y * (inv_b/total_inv)
                    rel_vel_y = a.velocity_y - b.velocity_y

                    if dy < 0:
                        a.exact_y -= push_a
                        b.exact_y += push_b
                        if rel_vel_y > 0:
                            shared_vel = (a.velocity_y * a.mass + b.velocity_y * b.mass) / (a.mass + b.mass)
                            a.velocity_y = b.velocity_y = shared_vel
                    else:
                        a.exact_y += push_a
                        b.exact_y -= push_b
                        if rel_vel_y < 0: 
                            shared_vel = (a.velocity_y * a.mass + b.velocity_y * b.mass) / (a.mass + b.mass)
                            a.velocity_y = b.velocity_y = shared_vel
                    
                    # Friction
                    rel_vel_x = a.velocity_x - b.velocity_x
                    a.velocity_x -= rel_vel_x * (inv_a / total_inv) * 0.6
                    b.velocity_x += rel_vel_x * (inv_b / total_inv) * 0.6

                a.rect.x, a.rect.y = int(a.exact_x), int(a.exact_y)
                b.rect.x, b.rect.y = int(b.exact_x), int(b.exact_y)

    # 2. Balloon vs RoomObject Resolution
    for b in balloons:
        if b.popped or b.state == "AT_NOZZLE": continue
        for obj in objects:
            closest_x = max(obj.rect.left, min(b.x, obj.rect.right))
            closest_y = max(obj.rect.top, min(b.y, obj.rect.bottom))
            dx, dy = b.x - closest_x, b.y - closest_y
            dist = math.hypot(dx, dy)
            if dist < b.radius:
                if dist == 0:
                    nx, ny = 0.0, -1.0
                    overlap = b.radius
                else:
                    nx, ny = dx / dist, dy / dist
                    overlap = b.radius - dist
                    
                b.x += nx * overlap
                b.y += ny * overlap
                
                dot_product = b.velocity_x * nx + b.velocity_y * ny
                if dot_product < 0:
                    b.velocity_x -= 1.5 * dot_product * nx
                    b.velocity_y -= 1.5 * dot_product * ny
                    
                # Kinetic momentum transfer from fast balloon to heavy object
                if not obj.dragging:
                    obj.velocity_x -= (nx * dot_product * 0.5) / obj.mass 

    # 3. Balloon vs Balloon
    for i in range(len(balloons)):
        for j in range(i + 1, len(balloons)):
            b1, b2 = balloons[i], balloons[j]
            if not b1.popped and not b2.popped and b1.state != "AT_NOZZLE" and b2.state != "AT_NOZZLE":
                dx, dy = b2.x - b1.x, b2.y - b1.y
                dist = math.hypot(dx, dy)
                min_dist = b1.radius + b2.radius
                if 0 < dist < min_dist:
                    overlap = min_dist - dist
                    nx, ny = dx / dist, dy / dist

                    # NEW: Calculate mass proxies (Area = r^2)
                    m1, m2 = b1.radius ** 2, b2.radius ** 2
                    total_m = m1 + m2
                    
                    # Calculate inverse mass ratios (heavier objects move less)
                    ratio1 = m2 / total_m
                    ratio2 = m1 / total_m


                    b1.x -= nx * overlap * ratio1
                    b1.y -= ny * overlap * ratio1
                    b2.x += nx * overlap * ratio2
                    b2.y += ny * overlap * ratio2
                    
                    PUSH = 0.2
                    b1.velocity_x -= nx * overlap * PUSH * ratio1
                    
                    b1.velocity_y -= ny * overlap * PUSH * ratio1
                    b2.velocity_x += nx * overlap * PUSH * ratio2
                    b2.velocity_y += ny * overlap * PUSH * ratio2

                    rvx = b2.velocity_x - b1.velocity_x
                    rvy = b2.velocity_y - b1.velocity_y
                    tx, ty = -ny, nx
                    friction = (rvx * tx + rvy * ty) * 0.15
                    b1.velocity_x += tx * friction * 0.5
                    b1.velocity_y += ty * friction * 0.5
                    b2.velocity_x -= tx * friction * 0.5
                    b2.velocity_y -= ty * friction * 0.5