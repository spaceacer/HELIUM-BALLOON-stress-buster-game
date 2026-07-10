# balloon.py
import pygame
import math
import random
from settings import (
    MAX_BALLOON_RADIUS, DEFAULT_STRING_LENGTH, LIFT_MULTIPLIER, REEL_SPEED,
    SPRING_STIFFNESS, SPRING_DAMPING, DAMPING, CEILING_Y, HEIGHT, # <-- Added HEIGHT
    STRING_COLOR, NODE_COLOR, DANGER_THRESHOLD, MAX_STRING_TENSION,
    AIR_DENSITY, DRAG_COEFF, VERLET_SEGMENTS, VERLET_ITERATIONS, GRAVITY
)

class VerletNode:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.old_x = float(x)
        self.old_y = float(y)

class Balloon:
    def __init__(self, tank):
        self.tank = tank
        self.knot_x = tank.nozzle_x + 35
        self.knot_y = tank.nozzle_y + 6
        self.radius = 2.0  
        self.bulb_distance = 5.0
        self.state = "AT_NOZZLE" 
        self.helium_amount = 0.0
        
        self.dragging = False
        self.drag_type = None 
        self.attached_object = None
        self.attached_balloon = None   
        self.attach_u = 0.0            
        self.string_attached_balloons = []  
        self.string_length = DEFAULT_STRING_LENGTH
        
        self.x = float(self.knot_x)
        self.y = float(self.knot_y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.node_x = float(self.knot_x)
        self.node_y = float(self.knot_y)
        self.theta = 90.0
        self.popped = False

        self.base_color = (random.randint(100, 255), random.randint(50, 220), random.randint(50, 255))
        
        # Initialize Verlet Physics Chain
        self.string_nodes = [VerletNode(self.knot_x, self.knot_y) for _ in range(VERLET_SEGMENTS + 1)]
        self.segment_length = self.string_length / VERLET_SEGMENTS

    def inflate(self):
        if self.state == "AT_NOZZLE" and not self.popped:
            self.radius += 0.3
            self.bulb_distance += 0.4
            self.helium_amount += 0.5
            inflation_ratio = self.radius / MAX_BALLOON_RADIUS
            self.theta = 90.0 - (inflation_ratio * 180.0)
            
    def check_over_inflation(self):
        return self.radius >= MAX_BALLOON_RADIUS

    def tie(self):
        if self.state == "AT_NOZZLE" and self.radius > 10 and not self.popped:
            self.state = "TIED_TO_TANK"
            self.node_x = float(self.tank.top_tie_x)
            self.node_y = float(self.tank.top_tie_y)
            # Instantly align string particles to avoid dramatic initialization snapping
            for node in self.string_nodes:
                node.x = node.old_x = self.node_x
                node.y = node.old_y = self.node_y
            
    def cut(self):
        if self.state == "TIED_TO_TANK":
            self.state = "CUT"
            self.node_x = self.x
            self.node_y = self.y + self.string_length + self.radius

    def detach(self):
        if self.attached_object is not None:
            if self in getattr(self.attached_object, 'attached_balloons', []):
                self.attached_object.attached_balloons.remove(self)
            self.attached_object = None
        if self.attached_balloon is not None:
            if self in self.attached_balloon.string_attached_balloons:
                self.attached_balloon.string_attached_balloons.remove(self)
            self.attached_balloon = None

    def release_dependents(self):
        for dep in list(self.string_attached_balloons):
            dep.attached_balloon = None
            dep.state = "CUT"
            dep.node_x = dep.x
            dep.node_y = dep.y + dep.string_length + dep.radius
        self.string_attached_balloons.clear()
            
    def get_lift(self):
        return self.helium_amount * LIFT_MULTIPLIER
        
    def adjust_string(self, direction):
        if self.state == "TIED_TO_TANK":
            self.string_length += direction * REEL_SPEED
            self.string_length = max(10, self.string_length) 
            self.segment_length = self.string_length / VERLET_SEGMENTS

    def point_line_distance(self, px, py, x1, y1, x2, y2):
        line_mag = math.hypot(x2 - x1, y2 - y1)
        if line_mag == 0: return math.hypot(px - x1, py - y1)
        u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
        if u < 0.0 or u > 1.0:
            return min(math.hypot(px - x1, py - y1), math.hypot(px - x2, py - y2))
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        return math.hypot(px - ix, py - iy)

    def handle_event(self, event, room_objects, other_balloons=None):
        if self.popped or self.state == "AT_NOZZLE": return
        if other_balloons is None:
            other_balloons = []
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            dist_node = math.hypot(event.pos[0] - self.node_x, event.pos[1] - self.node_y)
            dist_bulb = math.hypot(event.pos[0] - self.x, event.pos[1] - self.y)
            dist_string = self.point_line_distance(event.pos[0], event.pos[1], self.knot_x, self.knot_y, self.node_x, self.node_y)
            
            grabbed = None
            if dist_node < 20 or dist_string < 15:
                grabbed = "NODE"
            elif dist_bulb < self.radius + 10:
                grabbed = "BALLOON"

            if grabbed:
                if event.button == 1: 
                    # LEFT CLICK: Only drag. Does not cut the string.
                    # This allows you to rearrange nodes on objects naturally.
                    self.dragging = True
                    self.drag_type = grabbed
                elif event.button == 3: 
                    # RIGHT CLICK: Dedicated detach command.
                    if self.state == "ATTACHED":
                        self.state = "CUT"
                        self.detach()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:
                self.dragging = False
                if self.drag_type == "NODE":
                    landed = False
                    for obj in room_objects:
                        if obj.rect.collidepoint(event.pos):
                            self.state = "ATTACHED"
                            self.attached_object = obj
                            obj.attached_balloons.append(self)
                            self.master_anchor_offset_x = event.pos[0] - obj.rect.x
                            self.master_anchor_offset_y = event.pos[1] - obj.rect.y
                            self.node_x, self.node_y = float(event.pos[0]), float(event.pos[1])
                            landed = True
                            break
                    
                    if not landed:
                        best_host, best_dist = None, 18
                        for ob in other_balloons:
                            if ob is self or ob.popped or ob.state == "AT_NOZZLE" or ob.attached_balloon is self:
                                continue
                            d = self.point_line_distance(event.pos[0], event.pos[1], ob.knot_x, ob.knot_y, ob.node_x, ob.node_y)
                            if d < best_dist:
                                best_dist, best_host = d, ob
                        
                        if best_host is not None:
                            seg_dx = best_host.node_x - best_host.knot_x
                            seg_dy = best_host.node_y - best_host.knot_y
                            seg_len2 = seg_dx * seg_dx + seg_dy * seg_dy
                            u = max(0.0, min(1.0, ((event.pos[0] - best_host.knot_x) * seg_dx + (event.pos[1] - best_host.knot_y) * seg_dy) / seg_len2)) if seg_len2 > 0 else 1.0
                            self.state = "ATTACHED"
                            self.attached_balloon = best_host
                            self.attach_u = u
                            best_host.string_attached_balloons.append(self)
                            self.node_x, self.node_y = float(event.pos[0]), float(event.pos[1])

    def update(self):
        if self.popped: return

        # 1. Nozzle Tracking Setup
        if self.state == "AT_NOZZLE":
            self.node_x = float(self.tank.nozzle_x + 35)
            self.node_y = float(self.tank.nozzle_y + 6)
            self.knot_x = self.node_x
            self.knot_y = self.node_y
            
            if not hasattr(self, 'angular_velocity'):
                self.angular_velocity = 0.0
                self.theta = 85.0  
                
            net_buoyancy = (self.radius - 12.0) * 0.05 
            torque = -net_buoyancy * math.cos(math.radians(self.theta))
            
            self.angular_velocity += torque
            self.angular_velocity *= 0.88  
            self.theta = max(-100.0, min(85.0, self.theta + self.angular_velocity))
            
            rad = math.radians(self.theta)
            shake_x, shake_y = 0.0, 0.0
            if self.radius > MAX_BALLOON_RADIUS * DANGER_THRESHOLD:
                intensity = (self.radius - (MAX_BALLOON_RADIUS * DANGER_THRESHOLD)) * 0.4
                shake_x = random.uniform(-intensity, intensity)
                shake_y = random.uniform(-intensity, intensity)
                
            self.x = self.knot_x + math.cos(rad) * self.bulb_distance + shake_x
            self.y = self.knot_y + math.sin(rad) * self.bulb_distance + shake_y
            return 

        # 2. Mouse Dragging Inputs
        if self.dragging:
            mx, my = pygame.mouse.get_pos()
            if self.drag_type == "NODE":
                self.node_x, self.node_y = float(mx), float(my)
            elif self.drag_type == "BALLOON":
                self.x, self.y = float(mx), float(my)
                self.velocity_x = self.velocity_y = 0.0

        # 3. Node Position Syncing
        if getattr(self, 'is_bouquet_member', False) and self.state == "ATTACHED" and self.attached_object is not None:
            obj = self.attached_object
            if not hasattr(self, 'node_vel_x'):
                self.node_vel_x, self.node_vel_y = 0.0, 0.0
                
            from settings import MASTER_STRING_LENGTH
            anchor_x = float(obj.rect.x + self.master_anchor_offset_x)
            anchor_y = float(obj.rect.y + self.master_anchor_offset_y)
            
            self.node_vel_y += GRAVITY * 0.5
            
            dx_b, dy_b = self.x - self.node_x, self.y - self.node_y
            dist_b = math.hypot(dx_b, dy_b)
            if dist_b > self.string_length + self.radius:
                ext_b = dist_b - (self.string_length + self.radius)
                self.node_vel_x += (dx_b / dist_b) * ext_b * SPRING_STIFFNESS * 0.5
                self.node_vel_y += (dy_b / dist_b) * ext_b * SPRING_STIFFNESS * 0.5
                
            dx_m, dy_m = self.node_x - anchor_x, self.node_y - anchor_y
            dist_m = math.hypot(dx_m, dy_m)
            if dist_m > MASTER_STRING_LENGTH:
                ext_m = dist_m - MASTER_STRING_LENGTH
                self.node_vel_x -= (dx_m / dist_m) * ext_m * SPRING_STIFFNESS
                self.node_vel_y -= (dy_m / dist_m) * ext_m * SPRING_STIFFNESS
                
            self.node_vel_x *= DAMPING
            self.node_vel_y *= DAMPING
            self.node_x += self.node_vel_x
            self.node_y += self.node_vel_y
            
            if dist_m > MASTER_STRING_LENGTH:
                self.node_x = anchor_x + (dx_m / dist_m) * MASTER_STRING_LENGTH
                self.node_y = anchor_y + (dy_m / dist_m) * MASTER_STRING_LENGTH
                
        elif self.state == "ATTACHED" and not (self.dragging and self.drag_type == "NODE"):
            if self.attached_object is not None:
                self.node_x = float(self.attached_object.rect.x + self.master_anchor_offset_x)
                self.node_y = float(self.attached_object.rect.y + self.master_anchor_offset_y)
            elif self.attached_balloon is not None:
                host = self.attached_balloon
                if host.popped:
                    self.attached_balloon, self.state = None, "CUT"
                else:
                    self.node_x = host.knot_x + (host.node_x - host.knot_x) * self.attach_u
                    self.node_y = host.knot_y + (host.node_y - host.knot_y) * self.attach_u
                    
        elif self.state == "TIED_TO_TANK" and not (self.dragging and self.drag_type == "NODE"):
            self.node_x, self.node_y = float(self.tank.top_tie_x), float(self.tank.top_tie_y)

        # 4. Aerodynamic Drag Engine
        if not (self.dragging and self.drag_type == "BALLOON"):
            self.velocity_y -= self.get_lift()
            speed = math.hypot(self.velocity_x, self.velocity_y)
            if speed > 0.001:
                cross_section_area = math.pi * (self.radius ** 2)
                drag_force = 0.5 * AIR_DENSITY * (speed ** 2) * DRAG_COEFF * cross_section_area
                effective_mass = self.radius * 0.8
                deceleration = drag_force / effective_mass
                self.velocity_x -= (self.velocity_x / speed) * deceleration
                self.velocity_y -= (self.velocity_y / speed) * deceleration

            self.x += self.velocity_x
            self.y += self.velocity_y

        if self.state == "CUT" and not (self.dragging and self.drag_type == "NODE"):
            self.node_x = self.x
            self.node_y = self.y + self.string_length + self.radius

        # 5. HIGH-STIFFNESS VERLET CONSTRAINT ENGINE
        # 5. HIGH-STIFFNESS VERLET CONSTRAINT ENGINE
        self.segment_length = self.string_length / VERLET_SEGMENTS
        dx, dy = self.x - self.node_x, self.y - self.node_y
        dist = math.hypot(dx, dy)
        
        # HARD CEILING SAFEGUARD: If the entire balloon bulb drifts past its max total length,
        # physically pull it back before solving segments to eliminate the elastic stretch.
        max_total_len = self.string_length + self.bulb_distance
        if dist > max_total_len and dist > 0.001:
            self.x = self.node_x + (dx / dist) * max_total_len
            self.y = self.node_y + (dy / dist) * max_total_len
            dx, dy = self.x - self.node_x, self.y - self.node_y
            dist = max_total_len

        if dist > 0.1:
            self.knot_x = self.x - (dx / dist) * self.bulb_distance
            self.knot_y = self.y - (dy / dist) * self.bulb_distance

        # Sync outer structural anchors before solving
        self.string_nodes[0].x, self.string_nodes[0].y = self.knot_x, self.knot_y
        self.string_nodes[-1].x, self.string_nodes[-1].y = self.node_x, self.node_y

        # Forward Verlet integration step
        for node in self.string_nodes[1:-1]:
            vx = (node.x - node.old_x) * DAMPING
            vy = (node.y - node.old_y) * DAMPING + GRAVITY * 0.12
            node.old_x, node.old_y = node.x, node.y
            node.x += vx
            node.y += vy

        # Run the multi-pass solver loop to keep string structure tight
        for _ in range(VERLET_ITERATIONS):
            for i in range(VERLET_SEGMENTS):
                n1, n2 = self.string_nodes[i], self.string_nodes[i+1]
                idx, idy = n2.x - n1.x, n2.y - n1.y
                idist = math.hypot(idx, idy)
                if idist > 0:
                    diff = (idist - self.segment_length) / idist
                    # 0.5 ratio splits correction evenly, making it robust
                    ox, oy = idx * 0.5 * diff, idy * 0.5 * diff
                    if i != 0:
                        n1.x += ox
                        n1.y += oy
                    if i + 1 != VERLET_SEGMENTS:
                        n2.x -= ox
                        n2.y -= oy
            
            # Lock ends down securely on every iteration pass
            self.string_nodes[0].x, self.string_nodes[0].y = self.knot_x, self.knot_y
            self.string_nodes[-1].x, self.string_nodes[-1].y = self.node_x, self.node_y

        # Calculate accurate, smoothed string segment tension output
        end_dx = self.string_nodes[-1].x - self.string_nodes[-2].x
        end_dy = self.string_nodes[-1].y - self.string_nodes[-2].y
        end_dist = math.hypot(end_dx, end_dy)
        
        # Pull delta scaled by string stiffness constants
        tension_force = max(0, end_dist - self.segment_length) * SPRING_STIFFNESS * 3.5

        # Check for structural rupture conditions
        if tension_force > MAX_STRING_TENSION and self.state in ["ATTACHED", "TIED_TO_TANK"]:
            self.detach()
            self.release_dependents()
            self.state = "CUT"
            self.node_x, self.node_y = self.x, self.y + self.string_length + self.radius
        
        elif tension_force > 0 and end_dist > 0.001:
            nx, ny = end_dx / end_dist, end_dy / end_dist
            if not (self.dragging and self.drag_type == "BALLOON"):
                self.velocity_x -= nx * tension_force * 0.4
                self.velocity_y -= ny * tension_force * 0.4

            if self.state == "ATTACHED" and self.attached_object is not None:
                self.attached_object.velocity_x += (nx * tension_force * 0.3) / self.attached_object.mass
                self.attached_object.velocity_y += (ny * tension_force * 0.3) / self.attached_object.mass

        # 6. Ceiling and Floor Collisions
        if self.y - self.radius < CEILING_Y:
            self.y = CEILING_Y + self.radius
            if self.velocity_y < 0: self.velocity_y = 0.0 
            
        # --- NEW: Floor Collision ---
        if self.y + self.radius > HEIGHT:
            self.y = HEIGHT - self.radius
            if self.velocity_y > 0: 
                self.velocity_y *= -0.3 # Add a slight soft bounce

    def get_body_points(self, segments=36):
        dist = math.hypot(self.knot_x - self.x, self.knot_y - self.y)
        if dist <= self.radius:
            return [(self.x + self.radius * math.cos(i/segments * 2 * math.pi), 
                     self.y + self.radius * math.sin(i/segments * 2 * math.pi)) for i in range(segments)]
        
        angle_to_knot = math.atan2(self.knot_y - self.y, self.knot_x - self.x)
        theta = math.acos(self.radius / dist)
        points = []
        start_angle = angle_to_knot + theta
        sweep_angle = 2 * math.pi - 2 * theta
        
        for i in range(segments + 1):
            current_angle = start_angle + (i / segments) * sweep_angle
            points.append((self.x + self.radius * math.cos(current_angle), self.y + self.radius * math.sin(current_angle)))
            
        points.append((self.knot_x, self.knot_y))
        return points

    def draw(self, alpha_surface, solid_surface):
        if self.popped: return
        
        inflation_ratio = min(1.0, self.radius / MAX_BALLOON_RADIUS)
        alpha_value = int(255 - (150 * inflation_ratio)) 
        
        color_rgb = self.base_color
        if self.state == "AT_NOZZLE" and self.radius > MAX_BALLOON_RADIUS * DANGER_THRESHOLD:
            if pygame.time.get_ticks() % 200 < 100:
                color_rgb = tuple(min(255, c + 40) for c in self.base_color)

        body_points = self.get_body_points()
        if len(body_points) >= 3:
            pygame.draw.polygon(alpha_surface, color_rgb + (alpha_value,), body_points)
        
        if self.radius > 5:
            shine_radius = int(self.radius * 0.22)
            pygame.draw.circle(alpha_surface, (255, 255, 255, int(200 - (80 * inflation_ratio))), 
                               (int(self.x - self.radius * 0.35), int(self.y - self.radius * 0.35)), shine_radius)

        if self.state != "AT_NOZZLE":
            node_pts = [(int(n.x), int(n.y)) for n in self.string_nodes]
            if len(node_pts) > 1:
                pygame.draw.lines(solid_surface, STRING_COLOR, False, node_pts, 2)
            pygame.draw.circle(solid_surface, NODE_COLOR, (int(self.node_x), int(self.node_y)), 8)