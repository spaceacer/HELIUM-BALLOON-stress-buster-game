import pygame
import asyncio
import math
import random

from settings import WIDTH, HEIGHT, BACKGROUND, ANVIL_COLOR, CRATE_COLOR, FRIDGE_COLOR, WEIGHT_COLOR, MAX_BALLOON_RADIUS
from entities import HeliumTank, RoomObject, Table, unified_physics_sweep
from balloon import Balloon
from scissor import Scissor
from magichand import MagicHand  
import sound

sound.init()
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Helium Stress Buster V4 - Deep Physics Edition")

async def main():
    clock = pygame.time.Clock()
    
    table = Table()
    table.rect = pygame.Rect(22, HEIGHT - 75, 112, 15)
    table.leg1 = pygame.Rect(33, HEIGHT - 60, 11, 60)
    table.leg2 = pygame.Rect(112, HEIGHT - 60, 11, 60)
    
    tank = HeliumTank()
    tank.x = 187
    tank.y = HEIGHT - 150
    tank.width = 60
    tank.height = 150
    tank.nozzle_x = tank.x + tank.width
    tank.nozzle_y = tank.y + 22
    tank.top_tie_x = tank.nozzle_x - 8
    tank.top_tie_y = tank.nozzle_y + 11

    scissor = Scissor(table.rect.centerx, table.rect.top - 20)
    magic_hand = MagicHand()
    
    objects = [
        RoomObject(375, HEIGHT - 68, 68, 68, 11.0, CRATE_COLOR, "Crate"),
        RoomObject(525, HEIGHT - 45, 90, 45, 37.0, ANVIL_COLOR, "Anvil"),
        RoomObject(675, HEIGHT - 128, 64, 128, 90.0, FRIDGE_COLOR, "Fridge"),
        RoomObject(825, HEIGHT - 30, 38, 30, 3.75, WEIGHT_COLOR, "Weight"),
        RoomObject(900, HEIGHT - 30, 45, 30, 7.5, WEIGHT_COLOR, "Weight")
    ]
    
    balloons = [Balloon(tank)]
    active_balloon = balloons[-1]
    gas_particles = []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            for bq in magic_hand.free_bouquets:
                bq.handle_event(event, objects)
                
            any_bouquet_dragging = any(bq.dragging_node for bq in magic_hand.free_bouquets)
            
            if not magic_hand.active:
                scissor.handle_event(event)
                for obj in objects:
                    obj.handle_event(event)
                for b in balloons:
                    b.handle_event(event, objects, balloons)
            else:
                magic_hand.handle_event(event, objects) 
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:  
                    magic_hand.toggle()
                    
                # --- UPDATED: TIE AND AUTO-SPAWN ---
                elif event.key == pygame.K_t and not magic_hand.active:
                    active_balloon.tie()
                    # If successfully tied, immediately spawn a fresh balloon for the nozzle
                    if active_balloon.state == "TIED_TO_TANK":
                        active_balloon = Balloon(tank)
                        balloons.append(active_balloon)
                        
                # --- UPDATED: MASS CUT RELEASE ---
                elif event.key == pygame.K_x and not magic_hand.active:
                    # Loop through the master list and cut EVERYTHING currently on the tank
                    for b in balloons:
                        if b.state == "TIED_TO_TANK":
                            b.cut()
                            
                    # Safety catch: Ensure a balloon is always ready at the nozzle
                    if active_balloon.state != "AT_NOZZLE":
                        active_balloon = Balloon(tank)
                        balloons.append(active_balloon)
                        
                elif event.key == pygame.K_SPACE and not magic_hand.active:
                    if active_balloon.state == "AT_NOZZLE" and not active_balloon.popped:
                        sound.start_inflate()
                        
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    sound.stop_inflate()

        if active_balloon.state in ["CUT", "ATTACHED"] and not magic_hand.active:
            active_balloon = Balloon(tank)
            balloons.append(active_balloon)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and not magic_hand.active:
            
            # --- NEW: Lock string lengths of previously tied balloons ---
            for b in balloons:
                if b.state == "TIED_TO_TANK" and b != active_balloon:
                    b.string_locked = True
                    
            active_balloon.inflate()

            if active_balloon.state == "AT_NOZZLE":
                for _ in range(3):
                    gas_particles.append({
                        "x": float(tank.nozzle_x + 10),
                        "y": float(tank.nozzle_y + 6 + random.uniform(-4, 4)),
                        "vx": random.uniform(4, 7),
                        "vy": random.uniform(-2, 2),
                        "life": 1.0
                    })
            
            if active_balloon.check_over_inflation():
                sound.stop_inflate()  
                active_balloon.popped = True
                active_balloon.release_dependents()
                sound.play_pop()
                
                exp_x, exp_y = active_balloon.x, active_balloon.y
                for b in balloons:
                    if b != active_balloon and b.state != "AT_NOZZLE":
                        dist = math.hypot(b.x - exp_x, b.y - exp_y)
                        if dist < 400: 
                            force = (400 - dist) * 0.08
                            angle = math.atan2(b.y - exp_y, b.x - exp_x)
                            b.velocity_x += math.cos(angle) * force
                            b.velocity_y += math.sin(angle) * force
                            
                active_balloon = Balloon(tank)
                balloons.append(active_balloon)
        
        elif not keys[pygame.K_SPACE]:
            sound.stop_inflate()
            
        # --- UPDATED: Adjust string lengths ONLY for unlocked balloons ---
        if keys[pygame.K_UP] and not magic_hand.active:
            for b in balloons:
                if b.state == "TIED_TO_TANK" and not getattr(b, 'string_locked', False):
                    b.adjust_string(-1) 
                    
        if keys[pygame.K_DOWN] and not magic_hand.active:
            for b in balloons:
                if b.state == "TIED_TO_TANK" and not getattr(b, 'string_locked', False):
                    b.adjust_string(1) 

        # -----------------------------
        # 1. Update Core Elements
        # -----------------------------
        if not magic_hand.active:
            scissor.update()
        magic_hand.update(balloons, objects)  
        
        for obj in objects:
            obj.update()
        for b in balloons:
            b.update()

        # -----------------------------
        # 2. UNIFIED PHYSICS ENGINE SWEEP
        # -----------------------------
        unified_physics_sweep(objects, balloons)

        # -----------------------------
        # 3. Scissor Cutting Logic
        # -----------------------------
        tip_x, tip_y = scissor.blade_tip
        if not magic_hand.active:
            for b in balloons:
                if not b.popped and b.state != "AT_NOZZLE":
                    if math.hypot(b.x - tip_x, b.y - tip_y) < b.radius:
                        b.popped = True
                        b.detach()
                        b.release_dependents()
                        sound.play_pop()
                    elif b.state in ["TIED_TO_TANK", "CUT", "ATTACHED"]:
                        # Iterate through the new Verlet nodes for collision tracking against scissors
                        for i in range(len(b.string_nodes) - 1):
                            string_dist = b.point_line_distance(tip_x, tip_y, b.string_nodes[i].x, b.string_nodes[i].y, b.string_nodes[i+1].x, b.string_nodes[i+1].y)
                            if string_dist < 8: 
                                b.detach()
                                b.release_dependents()
                                b.state = "CUT"
                                b.node_x, b.node_y = b.x, b.y + b.string_length + b.radius
                                break

        # -----------------------------
        # 4. Render Stage
        # -----------------------------
        screen.fill(BACKGROUND)
        table.draw(screen)
        tank.draw(screen)
        if not magic_hand.active:
            scissor.draw(screen)
            
        for obj in objects:
            obj.draw(screen)
            
        alpha_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for b in balloons:
            b.draw(alpha_surface, screen)
            
        screen.blit(alpha_surface, (0, 0))
        magic_hand.draw(screen)  

        for p in gas_particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.08
            if p["life"] <= 0:
                gas_particles.remove(p)
            else:
                alpha_val = int(255 * p["life"])
                p_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (200, 220, 255, alpha_val), (2, 2), 2)
                screen.blit(p_surf, (int(p["x"]), int(p["y"])))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())