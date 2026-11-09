"""Neon Defender: a dependency-free Tkinter arcade space shooter."""
import json
import math
import random
import time
import tkinter as tk
from pathlib import Path

WIDTH, HEIGHT = 900, 650
BG = '#080e20'
CYAN = '#48e5ff'
PINK = '#ff5e91'
GOLD = '#ffd166'
WHITE = '#eaf2ff'
SAVE = Path.home() / '.neon_defender_highscore.json'


class Game:
    def __init__(self, root):
        self.root = root
        root.title('Neon Defender | Space Shooter')
        root.geometry('900x720')
        root.minsize(900, 720)
        root.configure(bg=BG)
        self.header = tk.Frame(root, bg='#121c35', height=55)
        self.header.pack(fill='x')
        self.status = tk.Label(self.header, bg='#121c35', fg=WHITE,
                               font=('Consolas', 14, 'bold'), anchor='w', padx=15)
        self.status.pack(side='left', fill='both', expand=True)
        for label, command in [('New Game', self.new_game), ('Pause / Resume', self.toggle_pause),
                               ('Help', self.help), ('Exit', self.exit_game)]:
            tk.Button(self.header, text=label, command=command, bg='#263b61', fg=WHITE,
                      activebackground='#345a85', activeforeground=WHITE, relief='flat',
                      font=('Segoe UI', 10, 'bold'), padx=10, pady=8).pack(side='left', padx=4)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG,
                                highlightthickness=0)
        self.canvas.pack()
        self.keys = set()
        root.bind('<KeyPress>', self.key_down)
        root.bind('<KeyRelease>', self.key_up)
        root.protocol('WM_DELETE_WINDOW', self.exit_game)
        self.stars = [[random.randrange(WIDTH), random.randrange(HEIGHT), random.uniform(.5, 2.4)]
                      for _ in range(90)]
        self.high = self.read_high()
        self.last = time.perf_counter()
        self.new_game()
        self.loop()

    def read_high(self):
        try:
            return max(0, int(json.loads(SAVE.read_text()).get('high_score', 0)))
        except (OSError, ValueError, TypeError):
            return 0

    def save_high(self):
        try:
            SAVE.write_text(json.dumps({'high_score': self.high}))
        except OSError:
            pass

    def new_game(self):
        self.player = [WIDTH / 2, HEIGHT - 70]
        self.hp = 3
        self.score = 0
        self.wave = 1
        self.enemies = []
        self.shots = []
        self.enemy_shots = []
        self.powerups = []
        self.particles = []
        self.cooldown = 0
        self.spawn_timer = 0.7
        self.invuln = 1.5
        self.rapid = 0
        self.state = 'playing'
        self.keys.clear()
        self.last = time.perf_counter()

    def key_down(self, event):
        key = event.keysym.lower()
        if key == 'p':
            self.toggle_pause()
        elif key == 'r':
            self.new_game()
        elif key == 'escape':
            self.exit_game()
        self.keys.add(key)

    def key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def toggle_pause(self):
        if self.state == 'playing':
            self.state = 'paused'
        elif self.state == 'paused':
            self.state = 'playing'
            self.last = time.perf_counter()

    def help(self):
        from tkinter import messagebox
        was_playing = self.state == 'playing'
        if was_playing:
            self.state = 'paused'
        messagebox.showinfo('How to play',
            'MOVE: Arrow keys or A / D\nSHOOT: Space\nPAUSE: P\nRESTART: R\nEXIT: Esc\n\n'
            'Destroy enemies, dodge their shots, and collect falling power-ups.\n'
            'Gold = rapid fire | Green = heal (up to 5 lives).\n'
            'Survive to reach higher waves!')
        if was_playing and self.state == 'paused':
            self.state = 'playing'
            self.last = time.perf_counter()

    def exit_game(self):
        from tkinter import messagebox
        if messagebox.askyesno('Exit Neon Defender', 'Exit the game?'):
            self.root.destroy()

    def spawn_enemy(self):
        x = random.randint(35, WIDTH - 35)
        speed = random.uniform(70, 125) + self.wave * 10
        hp = 1 + (self.wave >= 3 and random.random() < .3)
        self.enemies.append({'x': x, 'y': -25, 'speed': speed, 'hp': hp,
                             'phase': random.random() * 6.28, 'fire': random.uniform(1.2, 3)})

    def explosion(self, x, y, color, count=12):
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(45, 180)
            self.particles.append([x, y, math.cos(angle) * speed,
                                   math.sin(angle) * speed, .55, color])

    def hit_player(self):
        if self.invuln > 0:
            return
        self.hp -= 1
        self.invuln = 1.4
        self.explosion(*self.player, PINK, 18)
        if self.hp <= 0:
            self.state = 'over'
            if self.score > self.high:
                self.high = self.score
                self.save_high()

    def update(self, dt):
        for star in self.stars:
            star[1] = (star[1] + star[2] * 35 * dt) % HEIGHT
        for p in self.particles[:]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0:
                self.particles.remove(p)
        if self.state != 'playing':
            return
        direction = ('right' in self.keys or 'd' in self.keys) - ('left' in self.keys or 'a' in self.keys)
        self.player[0] = max(25, min(WIDTH - 25, self.player[0] + direction * 360 * dt))
        self.cooldown = max(0, self.cooldown - dt)
        self.invuln = max(0, self.invuln - dt)
        self.rapid = max(0, self.rapid - dt)
        if 'space' in self.keys and self.cooldown <= 0:
            self.shots.append([self.player[0], self.player[1] - 22])
            self.cooldown = .12 if self.rapid else .28
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            self.spawn_timer = max(.3, 1.05 - self.wave * .055) * random.uniform(.7, 1.3)
        for shot in self.shots[:]:
            shot[1] -= 560 * dt
            if shot[1] < -10:
                self.shots.remove(shot)
        for shot in self.enemy_shots[:]:
            shot[1] += shot[2] * dt
            if shot[1] > HEIGHT + 10:
                self.enemy_shots.remove(shot)
            elif abs(shot[0] - self.player[0]) < 19 and abs(shot[1] - self.player[1]) < 19:
                self.enemy_shots.remove(shot)
                self.hit_player()
        for enemy in self.enemies[:]:
            enemy['y'] += enemy['speed'] * dt
            enemy['phase'] += dt * 2
            enemy['x'] += math.sin(enemy['phase']) * 24 * dt
            enemy['fire'] -= dt
            if enemy['fire'] <= 0 and enemy['y'] > 20:
                self.enemy_shots.append([enemy['x'], enemy['y'] + 18, 210 + self.wave * 12])
                enemy['fire'] = random.uniform(1.3, 3)
            if enemy['y'] > HEIGHT + 25:
                self.enemies.remove(enemy)
                self.hit_player()
                continue
            if abs(enemy['x'] - self.player[0]) < 30 and abs(enemy['y'] - self.player[1]) < 28:
                self.enemies.remove(enemy)
                self.explosion(enemy['x'], enemy['y'], PINK)
                self.hit_player()
                continue
            for shot in self.shots[:]:
                if abs(shot[0] - enemy['x']) < 24 and abs(shot[1] - enemy['y']) < 20:
                    self.shots.remove(shot)
                    enemy['hp'] -= 1
                    self.explosion(shot[0], shot[1], CYAN, 4)
                    if enemy['hp'] <= 0:
                        self.enemies.remove(enemy)
                        self.explosion(enemy['x'], enemy['y'], GOLD)
                        self.score += 10
                        if self.score > self.high:
                            self.high = self.score
                            self.save_high()
                        if random.random() < .12:
                            kind = random.choice(['rapid', 'heal'])
                            self.powerups.append([enemy['x'], enemy['y'], kind])
                        self.wave = 1 + self.score // 150
                    break
        for power in self.powerups[:]:
            power[1] += 115 * dt
            if power[1] > HEIGHT + 15:
                self.powerups.remove(power)
            elif abs(power[0] - self.player[0]) < 25 and abs(power[1] - self.player[1]) < 25:
                self.powerups.remove(power)
                if power[2] == 'rapid':
                    self.rapid = 8
                else:
                    self.hp = min(5, self.hp + 1)

    def draw(self):
        c = self.canvas
        c.delete('all')
        for x, y, speed in self.stars:
            r = speed / 1.8
            c.create_oval(x-r, y-r, x+r, y+r, fill='#4c6289', outline='')
        for p in self.particles:
            r = max(1, p[4] * 5)
            c.create_oval(p[0]-r, p[1]-r, p[0]+r, p[1]+r, fill=p[5], outline='')
        for x, y in self.shots:
            c.create_rectangle(x-3, y-13, x+3, y+10, fill=CYAN, outline='')
        for x, y, _ in self.enemy_shots:
            c.create_oval(x-5, y-5, x+5, y+5, fill=PINK, outline='')
        for e in self.enemies:
            x, y = e['x'], e['y']
            c.create_polygon(x, y+19, x-23, y-10, x, y-19, x+23, y-10,
                             fill=PINK if e['hp'] == 1 else '#c37dff', outline='#ffd3e1', width=2)
            c.create_oval(x-5, y-5, x+5, y+5, fill=BG, outline='')
        for x, y, kind in self.powerups:
            color = GOLD if kind == 'rapid' else '#65e6a7'
            c.create_oval(x-13, y-13, x+13, y+13, fill=color, outline=WHITE, width=2)
            c.create_text(x, y, text='R' if kind == 'rapid' else '+',
                          font=('Segoe UI', 13, 'bold'), fill=BG)
        if self.state != 'over' and (self.invuln <= 0 or int(time.perf_counter() * 9) % 2):
            x, y = self.player
            c.create_polygon(x, y-28, x-24, y+20, x, y+11, x+24, y+20,
                             fill=CYAN, outline=WHITE, width=2)
            c.create_polygon(x-8, y+17, x, y+34, x+8, y+17, fill=GOLD, outline='')
        if self.rapid:
            c.create_text(WIDTH-18, 20, anchor='ne', text=f'RAPID FIRE {self.rapid:.0f}s',
                          fill=GOLD, font=('Consolas', 13, 'bold'))
        if self.state in ('paused', 'over'):
            c.create_rectangle(160, 215, 740, 435, fill='#121c35', outline=CYAN, width=2)
            c.create_text(WIDTH/2, 275, text='PAUSED' if self.state == 'paused' else 'GAME OVER',
                          font=('Segoe UI', 38, 'bold'), fill=WHITE)
            c.create_text(WIDTH/2, 345,
                          text='Press P to resume' if self.state == 'paused' else f'Final score: {self.score}',
                          font=('Segoe UI', 18), fill=CYAN)
            c.create_text(WIDTH/2, 395, text='Press R for a new game',
                          font=('Segoe UI', 14), fill=GOLD)
        self.status.config(text=f'NEON DEFENDER    SCORE {self.score:04d}    HIGH {self.high:04d}'
                                f'    WAVE {self.wave}    LIVES {self.hp}')

    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, .05)
        self.last = now
        self.update(dt)
        self.draw()
        self.root.after(16, self.loop)


if __name__ == '__main__':
    app = tk.Tk()
    Game(app)
    app.mainloop()
