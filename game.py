# space_shooter.py
# Полноценный 2D космический шутер на pygame — игрок, волны врагов, босс, пули, power-ups, эффекты.
# Требует: pip install pygame

import pygame
import random
import math
import json
from pathlib import Path

# ---------- Настройки ----------
WIDTH, HEIGHT = 900, 600
FPS = 60
PLAYER_SPEED = 6
BULLET_SPEED = 12
ENEMY_BULLET_SPEED = 5
START_LIVES = 3
HIGHSCORE_FILE = Path("ss_highscore.json")

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter — Advanced Demo")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)
big_font = pygame.font.SysFont("consolas", 36)

# ---------- Утилиты ----------
def clamp(x, a, b):
    return max(a, min(b, x))

def load_highscore():
    if HIGHSCORE_FILE.exists():
        try:
            return json.loads(HIGHSCORE_FILE.read_text()).get("highscore", 0)
        except:
            return 0
    return 0

def save_highscore(v):
    HIGHSCORE_FILE.write_text(json.dumps({"highscore": v}))

# ---------- Классы игровых объектов ----------
class Particle:
    def __init__(self, pos, vel, life, size, color):
        self.pos = list(pos)
        self.vel = list(vel)
        self.life = life
        self.size = size
        self.color = color

    def update(self, dt):
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.life -= dt

    def draw(self, surf):
        if self.life > 0:
            alpha = clamp(int(255 * (self.life / 1.0)), 0, 255)
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            surf.blit(s, (self.pos[0] - self.size, self.pos[1] - self.size))

class Bullet:
    def __init__(self, x, y, dx, dy, color=(255,255,0), owner="player", dmg=1):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.color = color
        self.owner = owner
        self.radius = 4
        self.dmg = dmg

    def update(self, dt):
        self.x += self.dx * dt
        self.y += self.dy * dt

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)

    def offscreen(self):
        return self.x < -50 or self.x > WIDTH+50 or self.y < -50 or self.y > HEIGHT+50

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 80
        self.speed = PLAYER_SPEED
        self.w = 34
        self.h = 44
        self.cooldown = 0
        self.hp = 5
        self.max_hp = 5
        self.lives = START_LIVES
        self.power = 1  # how many bullets per shot or strength
        self.score = 0
        self.invuln_timer = 0

    def update(self, keys, dt):
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.x -= self.speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.x += self.speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.y -= self.speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.y += self.speed * dt

        # bounds
        self.x = clamp(self.x, 20, WIDTH-20)
        self.y = clamp(self.y, HEIGHT//2, HEIGHT-20)

        if self.cooldown > 0:
            self.cooldown -= dt
        if self.invuln_timer > 0:
            self.invuln_timer -= dt

    def draw(self, surf):
        # draw ship: triangle + engine glow
        cx, cy = int(self.x), int(self.y)
        points = [(cx, cy-18), (cx-16, cy+16), (cx+16, cy+16)]
        if self.invuln_timer % 0.3 < 0.15:
            col = (255,255,255)
        else:
            col = (180, 220, 255)
        pygame.draw.polygon(surf, col, points)
        # engine flame
        pygame.draw.polygon(surf, (255,140,0), [(cx, cy+12), (cx-6, cy+20), (cx+6, cy+20)])

    def shoot(self):
        if self.cooldown > 0:
            return []
        self.cooldown = 0  # seconds
        bullets = []
        if self.power == 10:
            bullets.append(Bullet(self.x, self.y-22, 0, -BULLET_SPEED))
        elif self.power == 2:
            bullets.append(Bullet(self.x-6, self.y-20, -0.5, -BULLET_SPEED))
            bullets.append(Bullet(self.x+6, self.y-20, 0.5, -BULLET_SPEED))
        else:
            # spread of 5
            angles = [-0.2, -0.1, 0, 0.1, 0.2]
            for a in angles:
                bullets.append(Bullet(self.x + a*10, self.y-20, a*BULLET_SPEED, -BULLET_SPEED))
        return bullets

    def hurt(self, dmg):
        if self.invuln_timer > 0:
            return False
        self.hp -= dmg
        self.invuln_timer = 5
        return True

class Enemy:
    def __init__(self, x, y, hp=2, typ=0):
        self.x = x
        self.y = y
        self.hp = hp
        self.radius = 18 if typ==0 else 26
        self.typ = typ
        self.speed = 1 + typ*0.3
        self.phase = random.random()*math.pi*2
        self.shoot_timer = random.uniform(1.2,3.0) if typ>0 else random.uniform(2.0,4.0)

    def update(self, dt):
        # simple movement: down + sinus
        self.phase += dt*2
        self.x += math.sin(self.phase) * 40 * dt
        self.y += self.speed * 40 * dt
        self.shoot_timer -= dt

    def draw(self, surf):
        # draw a rounded enemy shape
        color = (255,120,120) if self.typ==0 else (255,200,80)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (0,0,0), (int(self.x-6), int(self.y-6)), int(self.radius*0.3))

    def should_shoot(self):
        return self.shoot_timer <= 0

    def reset_shoot(self):
        self.shoot_timer = random.uniform(1.0,3.0)

class Boss:
    def __init__(self):
        self.x = WIDTH//2
        self.y = -120
        self.hp = 150
        self.t = 0
        self.radius = 70
        self.phase = 0
        self.shoot_timer = 0.6

    def update(self, dt):
        self.t += dt
        # move into screen
        if self.y < 120:
            self.y += 30 * dt
        else:
            self.phase += dt*1.5
            self.x = WIDTH//2 + math.sin(self.phase)*200

        self.shoot_timer -= dt

    def draw(self, surf):
        # big boss with segments
        cx, cy = int(self.x), int(self.y)
        for i in range(4):
            r = self.radius - i*14
            pygame.draw.circle(surf, (130+i*20, 50+i*30, 200 - i*20), (cx, cy), r)
        # eyes
        pygame.draw.circle(surf, (0,0,0), (cx-30, cy-10), 10)
        pygame.draw.circle(surf, (0,0,0), (cx+30, cy-10), 10)

    def should_shoot(self):
        return self.shoot_timer <= 0

    def reset_shoot(self):
        self.shoot_timer = 0.6

# Power-ups: health restore, power increase, score boost
class PowerUp:
    TYPES = ["hp", "power", "score"]
    def __init__(self, x, y, typ=None):
        self.x = x
        self.y = y
        self.typ = typ if typ else random.choice(PowerUp.TYPES)
        self.timer = 8.0

    def update(self, dt):
        self.y += 40 * dt
        self.timer -= dt

    def draw(self, surf):
        colors = {"hp": (0,200,0), "power": (50,150,255), "score": (255,215,0)}
        pygame.draw.rect(surf, colors[self.typ], (int(self.x)-10, int(self.y)-10, 20, 20))
        pygame.draw.rect(surf, (0,0,0), (int(self.x)-10, int(self.y)-10, 20, 20), 2)

# ---------- Game class ----------
class Game:
    def __init__(self):
        self.player = Player()
        self.bullets = []
        self.e_bullets = []
        self.enemies = []
        self.particles = []
        self.powerups = []
        self.spawn_timer = 1.0
        self.wave = 1
        self.wave_counter = 0
        self.boss = None
        self.game_over = False
        self.paused = False
        self.highscore = load_highscore()

    def spawn_wave(self):
        # spawn enemies based on wave
        cnt = 5 + self.wave*2
        for i in range(cnt):
            x = random.randint(60, WIDTH-60)
            y = random.randint(-300, -60)
            typ = 1 if random.random() < min(0.3, self.wave*0.05) else 0
            hp = 3 if typ==1 else 1 + self.wave//3
            self.enemies.append(Enemy(x, y, hp=hp, typ=typ))
        self.wave += 1

    def update(self, dt, keys):
        if self.game_over or self.paused:
            return

        self.player.update(keys, dt)

        # player shooting
        if keys[pygame.K_SPACE]:
            new = self.player.shoot()
            for b in new:
                self.bullets.append(b)
                # small particles
                for _ in range(4):
                    a = random.uniform(-1,1)
                    self.particles.append(Particle((b.x, b.y+6), (a*20, 0.5*random.random()*40), 0.5, 2, (255,200,0)))

        # spawn waves
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_wave()
            self.spawn_timer = max(2.0, 6.0 - self.wave*0.2)

        # boss spawn
        if self.wave >= 6 and self.boss is None and random.random() < 0.01:
            self.boss = Boss()

        # update bullets
        for b in self.bullets[:]:
            b.update(dt)
            if b.offscreen():
                self.bullets.remove(b)

        for b in self.e_bullets[:]:
            b.update(dt)
            if b.offscreen():
                self.e_bullets.remove(b)

        # update enemies
        for e in self.enemies[:]:
            e.update(dt)
            if e.y > HEIGHT + 80:
                self.enemies.remove(e)
                continue
            if e.should_shoot():
                # enemy fires toward player
                angle = math.atan2(self.player.y - e.y, self.player.x - e.x)
                dx = math.cos(angle)*ENEMY_BULLET_SPEED*10
                dy = math.sin(angle)*ENEMY_BULLET_SPEED*10
                self.e_bullets.append(Bullet(e.x, e.y+10, dx, dy, color=(255,100,100), owner="enemy"))
                e.reset_shoot()

        # update boss
        if self.boss:
            self.boss.update(dt)
            if self.boss.should_shoot():
                # radial spray and targeted bullets
                for i in range(12):
                    ang = i*(2*math.pi/12) + random.uniform(-0.2,0.2)
                    dx = math.cos(ang)*6
                    dy = math.sin(ang)*6
                    self.e_bullets.append(Bullet(self.boss.x + math.cos(ang)*40, self.boss.y + math.sin(ang)*40, dx, dy, color=(255,80,80), owner="enemy"))
                # aimed bullets
                ang = math.atan2(self.player.y - self.boss.y, self.player.x - self.boss.x)
                for k in range(3):
                    a = ang + (k-1)*0.15
                    self.e_bullets.append(Bullet(self.boss.x, self.boss.y+30, math.cos(a)*8, math.sin(a)*8, color=(255,160,80), owner="enemy"))
                self.boss.reset_shoot()
            if self.boss.y > HEIGHT + 200:
                self.boss = None

        # update powerups
        for p in self.powerups[:]:
            p.update(dt)
            if p.timer <= 0 or p.y > HEIGHT + 20:
                self.powerups.remove(p)

        # collisions: player bullets -> enemies
        for b in self.bullets[:]:
            hit = False
            if self.boss:
                dist = math.hypot(b.x - self.boss.x, b.y - self.boss.y)
                if dist < self.boss.radius:
                    self.boss.hp -= b.dmg
                    hit = True
                    self.spawn_explosion(b.x, b.y, 8, (255,200,60))
                    if self.boss.hp <= 0:
                        self.spawn_explosion(self.boss.x, self.boss.y, 60, (255,100,100))
                        self.player.score += 1000
                        self.boss = None
                        # drop power-ups
                        for _ in range(3):
                            self.powerups.append(PowerUp(self.player.x + random.randint(-80,80), -50, typ=random.choice(["power","hp"])))
            for e in self.enemies[:]:
                dist = math.hypot(b.x - e.x, b.y - e.y)
                if dist < e.radius + b.radius:
                    e.hp -= b.dmg
                    hit = True
                    self.spawn_explosion(b.x, b.y, 4, (255,180,60))
                    if e.hp <= 0:
                        self.enemies.remove(e)
                        self.player.score += 50 + (e.typ*25)
                        # chance to drop powerup
                        if random.random() < 0.18:
                            self.powerups.append(PowerUp(e.x, e.y))
            if hit and b in self.bullets:
                try:
                    self.bullets.remove(b)
                except:
                    pass

        # collisions: enemy bullets -> player
        for eb in self.e_bullets[:]:
            dist = math.hypot(eb.x - self.player.x, eb.y - self.player.y)
            if dist < eb.radius + 14:
                if self.player.hurt(1):
                    self.spawn_explosion(self.player.x, self.player.y, 18, (255,40,40))
                    # lose hp, maybe life
                    if self.player.hp <= 0:
                        self.player.lives -= 1
                        if self.player.lives <= 0:
                            self.game_over = True
                            if self.player.score > self.highscore:
                                self.highscore = self.player.score
                                save_highscore(self.highscore)
                        else:
                            # respawn
                            self.player.hp = self.player.max_hp
                            self.player.invuln_timer = 1.0
                try:
                    self.e_bullets.remove(eb)
                except:
                    pass

        # collisions: enemies -> player (touch)
        for e in self.enemies[:]:
            dist = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if dist < e.radius + 14:
                if self.player.hurt(1):
                    self.spawn_explosion(e.x, e.y, 20, (255,120,60))
                    try:
                        self.enemies.remove(e)
                    except:
                        pass

        # collisions: player -> powerups
        for p in self.powerups[:]:
            dist = math.hypot(p.x - self.player.x, p.y - self.player.y)
            if dist < 20 + 14:
                if p.typ == "hp":
                    self.player.hp = min(self.player.max_hp, self.player.hp + 2)
                elif p.typ == "power":
                    self.player.power = min(3, self.player.power + 1)
                elif p.typ == "score":
                    self.player.score += 200
                try:
                    self.powerups.remove(p)
                except:
                    pass

        # tiny spawn of enemy bullets by enemies during updates above (already handled)
        # spawn occasional powerups
        if random.random() < 0.003:
            self.powerups.append(PowerUp(random.randint(40, WIDTH-40), -20))

        # update particles
        for part in self.particles[:]:
            part.update(dt)
            if part.life <= 0:
                self.particles.remove(part)

        # if wave empty and no boss -> next wave after short wait
        if not self.enemies and not self.boss:
            self.spawn_timer = min(self.spawn_timer, 1.2)
            if random.random() < 0.01:
                self.spawn_wave()

    def spawn_explosion(self, x, y, count, color):
        for _ in range(count):
            ang = random.uniform(0, math.pi*2)
            sp = random.uniform(20, 160)
            self.particles.append(Particle((x,y), (math.cos(ang)*sp, math.sin(ang)*sp), random.uniform(0.5,1.0), random.randint(2,5), color))

    def draw(self, surf):
        # background stars
        surf.fill((8, 12, 20))
        # moving starfield (particles)
        # draw all particles
        for part in self.particles:
            part.draw(surf)

        # draw enemies
        for e in self.enemies:
            e.draw(surf)

        if self.boss:
            self.boss.draw(surf)

        # draw bullets
        for b in self.bullets:
            b.draw(surf)
        for b in self.e_bullets:
            b.draw(surf)

        # draw powerups
        for p in self.powerups:
            p.draw(surf)

        # draw player
        self.player.draw(surf)

        # HUD
        self.draw_hud(surf)

        if self.paused:
            txt = big_font.render("PAUSED", True, (255,255,255))
            surf.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 40))
        if self.game_over:
            go = big_font.render("GAME OVER", True, (255,40,40))
            surf.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//2 - 40))
            sc = font.render(f"Score: {self.player.score}  Highscore: {self.highscore}", True, (255,255,255))
            surf.blit(sc, (WIDTH//2 - sc.get_width()//2, HEIGHT//2 + 10))
            info = font.render("R - restart   Q - quit", True, (200,200,200))
            surf.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT//2 + 40))

    def draw_hud(self, surf):
        # score
        score_s = font.render(f"Score: {self.player.score}", True, (200,200,255))
        surf.blit(score_s, (10, 8))
        # lives and HP
        lives_s = font.render(f"Lives: {self.player.lives}", True, (255,200,200))
        surf.blit(lives_s, (10, 30))
        hp_s = font.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, (200,255,200))
        surf.blit(hp_s, (10, 52))
        wave_s = font.render(f"Wave: {self.wave}", True, (200,200,200))
        surf.blit(wave_s, (WIDTH-120, 8))
        high_s = font.render(f"Highscore: {self.highscore}", True, (200,200,200))
        surf.blit(high_s, (WIDTH-220, 30))

    def restart(self):
        self.__init__()

# ---------- Main loop ----------
def main():
    g = Game()
    running = True
    last = pygame.time.get_ticks()/1000.0

    while running:
        now = pygame.time.get_ticks()/1000.0
        dt = now - last
        last = now
        if dt > 0.05:
            dt = 0.05  # clamp big dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    g.paused = not g.paused
                if event.key == pygame.K_r and g.game_over:
                    g.restart()
                if event.key == pygame.K_q and g.game_over:
                    running = False
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()
        g.update(dt, keys)
        g.draw(screen)

        # flip
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
