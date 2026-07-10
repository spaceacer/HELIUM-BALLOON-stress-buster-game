# magichand.py
import pygame
import math

from settings import (
    WIDTH, HEIGHT, MAGIC_HAND_COLOR, MASTER_NODE_COLOR, 
    MASTER_STRING_LENGTH, GRAVITY, DAMPING, SPRING_STIFFNESS, 
    STRING_COLOR, NODE_COLOR, SPRING_DAMPING
)

class FreeBouquet:
    def __init__(self, top_x, top_y, bottom_x, bottom_y, balloons):
        self.x = float(top_x)
        self.y = float(top_y)
        self.node_x = float(bottom_x)
        self.node_y = float(bottom_y)
        self.balloons = balloons
        
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.node_velocity_x = 0.0
        self.node_velocity_y = 0.0
        self.dragging_node = False
        self.attached_object = None
        self.is_bouquet_member = True
        
    def handle_event(self, event, room_objects):
        active_balloons = [b for b in self.balloons if not b.popped]
        if not active_balloons:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if math.hypot(event.pos[0] - self.node_x, event.pos[1] - self.node_y) < 15:
                    self.dragging_node = True
                    if self.attached_object:
                        if self in getattr(self.attached_object, 'attached_bouquets', []):
                            self.attached_object.attached_bouquets.remove(self)
                        self.attached_object = None
                        for b in active_balloons:
                            b.attached_object = None
                            b.is_bouquet_member = False

            elif event.button == 3 and self.dragging_node:
                for obj in room_objects:
                    if obj.rect.collidepoint(event.pos):
                        self.attached_object = obj
                        if not hasattr(obj, 'attached_bouquets'):
                            obj.attached_bouquets = []
                        obj.attached_bouquets.append(self)
                        
                        click_offset_x = event.pos[0] - obj.rect.x
                        click_offset_y = event.pos[1] - obj.rect.y
                        
                        # --- NEW: Distributed Multi-Point Anchoring (Creates Torque) ---
                        total_width = min(obj.rect.width - 20, len(active_balloons) * 20)
                        start_offset = click_offset_x - (total_width / 2)
                        
                        for i, b in enumerate(active_balloons):
                            b.attached_object = obj
                            if b not in obj.attached_balloons:
                                obj.attached_balloons.append(b)
                            b.state = "ATTACHED"
                            
                            # Spread tie locations evenly across the object width
                            spread_x = start_offset + (i * total_width / max(1, len(active_balloons)-1)) if len(active_balloons) > 1 else click_offset_x
                            b.master_anchor_offset_x = spread_x
                            b.master_anchor_offset_y = click_offset_y
                            b.is_bouquet_member = True
                            
                        self.dragging_node = False
                        break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_node = False

    def update(self, room_objects):
        # FIX: Ensure we constantly filter out balloons that just got CUT mid-frame
        active_balloons = [b for b in self.balloons if not b.popped and b.state != "CUT"]
        if not active_balloons:
            return

        if self.attached_object:
            b0 = active_balloons[0]
            self.node_x = float(self.attached_object.rect.x + b0.master_anchor_offset_x)
            self.node_y = float(self.attached_object.rect.y + b0.master_anchor_offset_y)
            self.node_velocity_x = self.node_velocity_y = 0.0
        elif self.dragging_node:
            mx, my = pygame.mouse.get_pos()
            self.node_x, self.node_y = float(mx), float(my)
            self.node_velocity_x = self.node_velocity_y = 0.0
        else:
            self.node_velocity_y += GRAVITY * 1.5
            
        self.velocity_y += GRAVITY * 0.5
        
        total_lift = sum(b.get_lift() for b in active_balloons)
        
        # Iterate over the safe, filtered list
        for b in active_balloons:
            dx, dy = b.x - self.x, b.y - self.y
            dist = math.hypot(dx, dy)
            if dist > b.string_length + b.radius:
                ext = dist - (b.string_length + b.radius)
                nx, ny = dx / dist, dy / dist
                force = (ext * SPRING_STIFFNESS) + ((b.velocity_x - self.velocity_x) * nx + (b.velocity_y - self.velocity_y) * ny) * SPRING_DAMPING
                self.velocity_x += nx * force
                self.velocity_y += ny * force
                
        dx, dy = self.node_x - self.x, self.node_y - self.y
        dist = math.hypot(dx, dy)
        if dist > MASTER_STRING_LENGTH:
            ext = dist - MASTER_STRING_LENGTH
            nx, ny = dx / dist, dy / dist
            force = (ext * SPRING_STIFFNESS * 2.0) + ((self.node_velocity_x - self.velocity_x) * nx + (self.node_velocity_y - self.velocity_y) * ny) * SPRING_DAMPING * 2.0
            self.velocity_x += nx * force
            self.velocity_y += ny * force
            if not self.dragging_node and not self.attached_object:
                self.node_velocity_x -= nx * force
                self.node_velocity_y -= ny * force
                
        MAX_SPEED = 25.0
        self.velocity_x = max(-MAX_SPEED, min(MAX_SPEED, self.velocity_x * DAMPING))
        self.velocity_y = max(-MAX_SPEED, min(MAX_SPEED, self.velocity_y * DAMPING))
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        if not self.dragging_node and not self.attached_object:
            self.node_velocity_x = max(-MAX_SPEED, min(MAX_SPEED, self.node_velocity_x * DAMPING))
            self.node_velocity_y = max(-MAX_SPEED, min(MAX_SPEED, self.node_velocity_y * DAMPING))
            if self.node_y > HEIGHT - 10:
                self.node_y, self.node_velocity_y, self.node_velocity_x = HEIGHT - 10, self.node_velocity_y * -0.3, self.node_velocity_x * 0.5
            self.node_x += self.node_velocity_x
            self.node_y += self.node_velocity_y
        
        for b in active_balloons:
            b.node_x, b.node_y, b.state = self.x, self.y, "MAGIC_GRABBED"
            
    def draw(self, surface):
        pygame.draw.line(surface, STRING_COLOR, (int(self.x), int(self.y)), (int(self.node_x), int(self.node_y)), 5)
        pygame.draw.circle(surface, MASTER_NODE_COLOR, (int(self.x), int(self.y)), 10)
        pygame.draw.circle(surface, NODE_COLOR, (int(self.node_x), int(self.node_y)), 8)


class MagicHand:
    def __init__(self):
        self.x = self.y = self.prev_x = self.prev_y = 0.0
        self.radius = 25
        self.active = False
        self.captured_balloons = []
        self.free_bouquets = []
        self.has_dropped_anchor = False
        self.anchor_x = self.anchor_y = self.anchor_velocity_x = self.anchor_velocity_y = 0.0

    def toggle(self):
        self.active = not self.active
        if not self.active:
            for b in self.captured_balloons:
                b.state, b.node_x, b.node_y = "CUT", b.x, b.y + b.string_length + b.radius
            self.captured_balloons.clear()
            self.has_dropped_anchor = False

    def line_intersection(self, p1, p2, p3, p4):
        den = (p4[1] - p3[1]) * (p2[0] - p1[0]) - (p4[0] - p3[0]) * (p2[1] - p1[1])
        if den == 0: return False
        ua = ((p4[0] - p3[0]) * (p1[1] - p3[1]) - (p4[1] - p3[1]) * (p1[0] - p3[0])) / den
        ub = ((p2[0] - p1[0]) * (p1[1] - p3[1]) - (p2[1] - p1[1]) * (p1[0] - p3[0])) / den
        return (0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0)

    def update(self, balloons, room_objects):
        for bq in self.free_bouquets: bq.update(room_objects)
        self.free_bouquets = [bq for bq in self.free_bouquets if any(not b.popped for b in bq.balloons)]
        
        self.prev_x, self.prev_y = self.x, self.y
        self.x, self.y = float(pygame.mouse.get_pos()[0]), float(pygame.mouse.get_pos()[1])

        if not self.active: return

        if not self.has_dropped_anchor:
            for b in balloons:
                if b.popped or b.state == "AT_NOZZLE" or b in self.captured_balloons: continue
                if self.line_intersection((self.prev_x, self.prev_y), (self.x, self.y), (b.knot_x, b.knot_y), (b.node_x, b.node_y)):
                    b.detach()
                    b.state = "MAGIC_GRABBED" 
                    self.captured_balloons.append(b)

            for b in self.captured_balloons:
                b.node_x, b.node_y = self.x, self.y
        else:
            self.anchor_velocity_y += GRAVITY * 1.5  
            dx, dy = self.anchor_x - self.x, self.anchor_y - self.y
            dist = math.hypot(dx, dy)
            if dist > MASTER_STRING_LENGTH:
                self.anchor_velocity_x -= (dx / dist) * SPRING_STIFFNESS * (dist - MASTER_STRING_LENGTH) * 2.0
                self.anchor_velocity_y -= (dy / dist) * SPRING_STIFFNESS * (dist - MASTER_STRING_LENGTH) * 2.0

            self.anchor_velocity_x *= DAMPING
            self.anchor_velocity_y *= DAMPING
            self.anchor_x += self.anchor_velocity_x
            self.anchor_y += self.anchor_velocity_y
            
            if self.anchor_y > HEIGHT - 10:
                self.anchor_y, self.anchor_velocity_y, self.anchor_velocity_x = HEIGHT - 10, 0.0, self.anchor_velocity_x * 0.5
            
            for b in self.captured_balloons:
                if not b.popped: b.node_x, b.node_y = self.x, self.y

    def handle_event(self, event, room_objects):
        for bq in self.free_bouquets: bq.handle_event(event, room_objects)

        if not self.active: return
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.captured_balloons and not self.has_dropped_anchor:
                self.has_dropped_anchor, self.anchor_x, self.anchor_y, self.anchor_velocity_x, self.anchor_velocity_y = True, self.x, self.y, 0.0, 0.0
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.has_dropped_anchor:
                anchored = False
                for obj in room_objects:
                    if obj.rect.collidepoint(event.pos):
                        click_offset_x = event.pos[0] - obj.rect.x
                        click_offset_y = event.pos[1] - obj.rect.y
                        
                        # --- NEW: Distributed Multi-Point Anchoring (Creates Torque) ---
                        total_width = min(obj.rect.width - 20, len(self.captured_balloons) * 20)
                        start_offset = click_offset_x - (total_width / 2)

                        for i, b in enumerate(self.captured_balloons):
                            b.attached_object = obj
                            obj.attached_balloons.append(b)
                            b.state = "ATTACHED" 
                            b.master_anchor_offset_x = start_offset + (i * total_width / max(1, len(self.captured_balloons)-1)) if len(self.captured_balloons) > 1 else click_offset_x
                            b.master_anchor_offset_y = click_offset_y
                            b.is_bouquet_member = True
                        anchored = True
                        break
                
                if not anchored:
                    self.free_bouquets.append(FreeBouquet(self.x, self.y, self.anchor_x, self.anchor_y, list(self.captured_balloons)))

                self.captured_balloons = []
                self.has_dropped_anchor = False

    def draw(self, surface):
        for bq in self.free_bouquets: bq.draw(surface)
        if not self.active: return
        pygame.draw.circle(surface, MAGIC_HAND_COLOR, (int(self.x), int(self.y)), self.radius, 2)
        if self.has_dropped_anchor:
            pygame.draw.line(surface, STRING_COLOR, (int(self.x), int(self.y)), (int(self.anchor_x), int(self.anchor_y)), 5)
            pygame.draw.circle(surface, MASTER_NODE_COLOR, (int(self.x), int(self.y)), 10)
            pygame.draw.circle(surface, NODE_COLOR, (int(self.anchor_x), int(self.anchor_y)), 8)