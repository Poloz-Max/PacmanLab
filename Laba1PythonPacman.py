# pacman_heuristics.py
# Pac-Man clone with funny ghost heuristics.
# Requirements:
#   - Python 3.x
#   - pygame (pip install pygame)
#
# Controls:
#   Arrows - move Pac-Man
#   D - change difficulty (easy <-> hard)
#   M - change maze variant
#   R - reset level
#   SPACE - restart game (if game over)
#   ESC - quit

import pygame, sys, random
from collections import deque

pygame.init()

TILE = 22
GRID_W, GRID_H = 29, 31
SCREEN_W, SCREEN_H = GRID_W * TILE, GRID_H * TILE + 29
FPS = 60

DIFFICULTIES = ["easy", "hard"]
DIFFICULTY = "easy"  # initial; can toggle with D

DIFFICULTY_PRESETS = {
    "easy": {"ghost_speed": 0.6, "frightened_time": FPS*6, "aggressiveness": 0.5},
    "hard": {"ghost_speed": 0.6, "frightened_time": FPS*4, "aggressiveness": 1.0},
}
# ----- Speed settings (lower = slower) -----
PACMAN_DELAY = {"easy": 6, "hard": 4}   # кількість кадрів між рухами Pacman
GHOST_DELAY = {"easy": 6, "hard": 6}   # кількість кадрів між рухами привидів

MAZE_VARIANTS = []

raw_maze_1 = [
"11111111111111111111111111111",
"1...........................1",
"1.111.11111.11.11111.111.11.1",
"1o111.11111.11.11111.111.11.1",
"1.111.11111.11.11111.111.11.1",
"1...........................1",
"1.111.11.1111111111.11.1111.1",
"1.111.11.1111111111.11.1111.1",
"1......1.....11.....1.......1",
"111111.11111 11 11111.1111111",
"     1.11111 11 11111.1      ",
"     1.11          11.1      ",
"     1.11 111--111 11.1      ",
"111111.11 1      1 11.1111111",
"      .   1      1   .       ",
"111111.11 1      1 11.1111111",
"     1.11 11111111 11.1      ",
"     1.11          11.1      ",
"     1.11 11111111 11.1      ",
"111111.11 11111111 11.1111111",
"1...........................1",
"1.111.11111111.11111.111.11.1",
"1.o...11111111.11111.11..o..1",
"1111.11....          11.11111",
"1.......1...................1",
"1.11111111.11.11.1111111111.1",
"1.11111111.11.11.1111111111.1",
"1...........................1",
"11111111111111111111111111111",
"11111111111111111111111111111",
"11111111111111111111111111111",
]
MAZE_VARIANTS.append([("1" if ch == "1" else "." if ch=="." else "o" if ch=="o" else "0") for ch in row] for row in raw_maze_1)
# convert to list of strings with cleaned chars
MAZE_VARIANTS[0] = []
for row in raw_maze_1:
    MAZE_VARIANTS[0].append("".join(ch if ch in "10o." else "0" for ch in row))

raw_maze_2 = [
"11111111111111111111111111111",
"1..............11............1",
"1.111111111111.11.1111111111.1",
"1.111111111111.11.1111111111.1",
"1.111111111111.11.1111111111.1",
"1............................1",
"1.111.11.111111111111.11.111.1",
"1.111.11.111111111111.11.111.1",
"1......1.....11..............1",
"111111.11111 11 11111.1111111",
"     1.11111 11 11111.1      ",
"     1.11          11.1      ",
"     1.11 111--111 11.1      ",
"111111.11 1      1 11.1111111",
"      .   1      1   .       ",
"111111.11 1      1 11.1111111",
"     1.11 11111111 11.1      ",
"     1.11          11.1      ",
"     1.11 11111111 11.1      ",
"111111.11 11111111 11.1111111",
"1...............o...........1",
"1.111111111111.11111.111111.1",
"1.o........................o1",
"111111111111          1111111",
"1...........................1",
"1.111111111.11.11.111111111.1",
"1.111111111.11.11.111111111.1",
"1...........................1",
"11111111111111111111111111111",
"11111111111111111111111111111",
"11111111111111111111111111111",
]
MAZE_VARIANTS.append([ "".join(ch if ch in "10o." else "0" for ch in row) for row in raw_maze_2 ])

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Pac-Man - Heuristics demo (D changes difficulty, M changes maze)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 16)

# utilities
def in_bounds(x,y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H

dirs = [(0,-1),(0,1),(-1,0),(1,0)]

# Maze class
class Maze:
    def __init__(self, layout):
        self.grid = [[0]*GRID_W for _ in range(GRID_H)]
        self.pellets = set()
        self.power = set()
        for y,row in enumerate(layout):
            for x,ch in enumerate(row):
                if x>=GRID_W or y>=GRID_H: continue
                if ch == "1":
                    self.grid[y][x] = 1
                elif ch == ".":
                    self.grid[y][x] = 0
                    self.pellets.add((x,y))
                elif ch == "o":
                    self.grid[y][x] = 0
                    self.power.add((x,y))
                else:
                    self.grid[y][x] = 0
    def is_wall(self,x,y):
        if not in_bounds(x,y): return True
        return self.grid[y][x] == 1
    def draw(self,surf):
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.grid[y][x] == 1:
                    pygame.draw.rect(surf,(20,20,120), (x*TILE,y*TILE,TILE,TILE))
        for (x,y) in self.pellets:
            pygame.draw.circle(surf,(200,180,50),(x*TILE+TILE//2,y*TILE+TILE//2),3)
        for (x,y) in self.power:
            pygame.draw.circle(surf,(255,100,100),(x*TILE+TILE//2,y*TILE+TILE//2),6)

# BFS next-step
def bfs_next(maze, start, goal):
    if start == goal: return start
    q = deque([start])
    prev = {start:None}
    while q:
        u = q.popleft()
        if u == goal: break
        ux,uy = u
        for dx,dy in dirs:
            v = (ux+dx, uy+dy)
            if not in_bounds(*v) or maze.is_wall(*v) or v in prev: continue
            prev[v] = u
            q.append(v)
    if goal not in prev: 
        return None
    cur = goal
    while prev[cur] != start and prev[cur] is not None:
        cur = prev[cur]
    return cur

class Pacman:
    def __init__(self,x,y):
        self.x=x; self.y=y
        self.dir=(0,0)
        self.next_dir=(0,0)
        self.lives=3
        self.move_timer = 0
        self.score=0
        self.power_timer=0
    def set_dir(self,d):
        self.next_dir=d
    def update(self, maze):
        self.move_timer += 1
        if self.move_timer < PACMAN_DELAY[DIFIC]:
            return
        self.move_timer = 0

        nx = self.x + self.next_dir[0]
        ny = self.y + self.next_dir[1]
        if not maze.is_wall(nx, ny):
            self.dir = self.next_dir
        tx = self.x + self.dir[0]
        ty = self.y + self.dir[1]
        if not maze.is_wall(tx, ty):
            self.x, self.y = tx, ty

        if (self.x, self.y) in maze.pellets:
            maze.pellets.remove((self.x, self.y))
            self.score += 10
        if (self.x, self.y) in maze.power:
            maze.power.remove((self.x, self.y))
            self.power_timer = DIFFICULTY_PRESETS[DIFIC]["frightened_time"]
            self.score += 50
        if self.power_timer > 0:
            self.power_timer -= 1
    def draw(self,surf):
        cx,cy = self.x*TILE+TILE//2, self.y*TILE+TILE//2
        pygame.draw.circle(surf,(255,220,0),(cx,cy),TILE//2-2)
        # eye
        ex = cx + (self.dir[0]*4 if self.dir else 0)
        ey = cy + (self.dir[1]*2 if self.dir else -4)
        pygame.draw.circle(surf,(0,0,0),(ex,ey),3)

class Ghost:
    COLORS = [(255,0,0),(255,160,0),(0,200,255),(255,0,255)]
    def __init__(self,name,x,y,color_idx,behavior):
        self.name=name
        self.x=x; self.y=y
        self.start=(x,y)
        self.color=Ghost.COLORS[color_idx%len(Ghost.COLORS)]
        self.behavior=behavior
        self.mode="chase"  # chase, scatter, frightened
        self.alive=True
        self.respawn_timer=0
        self.move_timer = 0
    def reset(self):
        self.x,self.y=self.start
        self.mode="chase"
        self.alive=True
        self.respawn_timer=0
    def update(self,maze,pacman,ghosts,preset):
        self.move_timer += 1
        if self.move_timer < GHOST_DELAY[DIFIC]:
            return
        self.move_timer = 0
        if not self.alive:
            self.respawn_timer -= 1
            if self.respawn_timer<=0: self.reset()
            return
        if pacman.power_timer>0:
            self.mode="frightened"
        else:
            if self.mode=="frightened": self.mode="chase"
        if self.mode=="frightened":
            # run randomly; occasionally move toward pellets
            choices=[]
            for dx,dy in dirs:
                nx,ny = self.x+dx, self.y+dy
                if not maze.is_wall(nx,ny): choices.append((nx,ny))
            if choices:
                if random.random()<0.15 and maze.pellets:
                    pellet = min(maze.pellets, key=lambda p:abs(p[0]-self.x)+abs(p[1]-self.y))
                    nxt=bfs_next(maze,(self.x,self.y),pellet)
                    if nxt: self.x,self.y = nxt
                    else: self.x,self.y=random.choice(choices)
                else:
                    self.x,self.y=random.choice(choices)
            return
        # normal: compute target from behavior
        target = self.behavior(self,maze,pacman,ghosts,preset)
        if target:
            nxt = bfs_next(maze,(self.x,self.y),target)
            if nxt:
                # some randomness depending on aggressiveness
                if random.random() < max(0.0,0.25 - 0.15 * preset["aggressiveness"]):
                    # lazy random step
                    choices=[]
                    for dx,dy in dirs:
                        nx,ny=self.x+dx,self.y+dy
                        if not maze.is_wall(nx,ny): choices.append((nx,ny))
                    if choices:
                        self.x,self.y=random.choice(choices)
                else:
                    self.x,self.y=nxt
            else:
                # wander
                choices=[]
                for dx,dy in dirs:
                    nx,ny=self.x+dx,self.y+dy
                    if not maze.is_wall(nx,ny): choices.append((nx,ny))
                if choices: self.x,self.y=random.choice(choices)
    def draw(self,surf):
        cx,cy = self.x*TILE+TILE//2,self.y*TILE+TILE//2
        if self.mode=="frightened":
            pygame.draw.circle(surf,(120,120,240),(cx,cy),TILE//2-2)
        else:
            pygame.draw.circle(surf,self.color,(cx,cy),TILE//2-2)
        pygame.draw.circle(surf,(255,255,255),(cx-6,cy-6),4)
        pygame.draw.circle(surf,(255,255,255),(cx+6,cy-6),4)
        pygame.draw.circle(surf,(0,0,0),(cx-6,cy-6),2)
        pygame.draw.circle(surf,(0,0,0),(cx+6,cy-6),2)

# ------------------ Heuristics (we ensure exactly 3 per difficulty) ------------------
# Shared helper
def manhattan(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])

# EASY heuristics (3):
def easy_chaser(self,maze,pacman,ghosts,preset):
    # simple chase current pacman tile
    return (pacman.x,pacman.y)

def easy_distracted(self,maze,pacman,ghosts,preset):
    # prefers pellets, occasionally chases
    if maze.pellets and random.random()<0.6:
        return min(maze.pellets, key=lambda p:manhattan(p,(self.x,self.y)))
    if manhattan((self.x,self.y),(pacman.x,pacman.y))<=4 and random.random()<0.8:
        return (pacman.x,pacman.y)
    return random.choice([(1,1),(GRID_W-2,1),(1,GRID_H-2),(GRID_W-2,GRID_H-2)])

def easy_wallhugger(self,maze,pacman,ghosts,preset):
    # go to tile near walls around pacman's area
    best=None;bestscore=-1
    for dx in range(-6,7):
        for dy in range(-6,7):
            tx,ty = pacman.x+dx,pacman.y+dy
            if not in_bounds(tx,ty) or maze.is_wall(tx,ty): continue
            score=0
            for ddx,ddy in dirs:
                if maze.is_wall(tx+ddx,ty+ddy): score+=1
            if score>bestscore:
                bestscore=score; best=(tx,ty)
    return best if best else (pacman.x,pacman.y)

# HARD heuristics (3):
def hard_ambusher(self,maze,pacman,ghosts,preset):
    # predict several steps ahead depending on aggressiveness
    steps = 3 + int(2 * preset["aggressiveness"])
    tx,ty = pacman.x + pacman.dir[0]*steps, pacman.y + pacman.dir[1]*steps
    if not in_bounds(tx,ty) or maze.is_wall(tx,ty):
        return (pacman.x,pacman.y)
    return (tx,ty)

def hard_confuser(self,maze,pacman,ghosts,preset):
    # teamplay: reflect pacman across first other ghost
    others = [g for g in ghosts if g is not self and g.alive]
    if others:
        leader=others[0]
        tx = 2*leader.x - pacman.x
        ty = 2*leader.y - pacman.y
        if in_bounds(tx,ty) and not maze.is_wall(tx,ty):
            return (tx,ty)
    return (pacman.x,pacman.y)

def hard_predator(self,maze,pacman,ghosts,preset):
    # prioritize closing distance; target a tile that minimizes distance but prefers corridors
    best=None;bestscore=9999
    for dx in range(-5,6):
        for dy in range(-5,6):
            tx,ty = pacman.x+dx,pacman.y+dy
            if not in_bounds(tx,ty) or maze.is_wall(tx,ty): continue
            # score: manhattan + penalty for openness (prefer corridors)
            openness = 4 - sum(1 for ddx,ddy in dirs if not maze.is_wall(tx+ddx,ty+ddy))
            score = manhattan((self.x,self.y),(tx,ty)) - int(1.5 * openness)
            if score < bestscore:
                bestscore = score; best=(tx,ty)
    return best if best else (pacman.x,pacman.y)

DIFF_BEHAVIORS = {
    "easy": [easy_chaser, easy_distracted, easy_wallhugger],
    "hard": [hard_ambusher, hard_confuser, hard_predator],
}

class Game:
    def __init__(self):
        self.diff = DIFFICULTY
        self.preset = DIFFICULTY_PRESETS[self.diff]
        self.maze_idx = 0
        self.maze = Maze(MAZE_VARIANTS[self.maze_idx])
        self.pacman = Pacman(14,23)
        self.ghosts = []
        self.level = 1
        self.message = ""
        self.prepare_ghosts()
        self.scatter_timer = FPS * 7

    def prepare_ghosts(self):
        self.ghosts = []
        pool = DIFF_BEHAVIORS[self.diff][:]  # три основні евристики
        positions = [(13,11),(14,11),(12,13)]  # стартові позиції для трьох привидів
        names = ["G1","G2","G3"]
        for i in range(3):
            beh = pool[i]
            g = Ghost(names[i], positions[i][0], positions[i][1], i, beh)
            self.ghosts.append(g)
    def change_difficulty(self):
        self.diff = "hard" if self.diff=="easy" else "easy"
        self.preset = DIFFICULTY_PRESETS[self.diff]
        self.message = f"Difficulty: {self.diff}"
        self.prepare_ghosts()

    def change_maze(self):
        self.maze_idx = (self.maze_idx + 1) % len(MAZE_VARIANTS)
        self.reset_level()
        self.message = f"Maze: {self.maze_idx+1}"

    def reset_level(self):
        self.maze = Maze(MAZE_VARIANTS[self.maze_idx])
        self.pacman = Pacman(14,23)
        for g in self.ghosts: g.reset()
        self.scatter_timer = FPS * 7

    def update(self):
        if self.pacman.lives <= 0:
            return
        self.pacman.update(self.maze)
        # toggle scatter every scatter_timer
        self.scatter_timer -= 1
        if self.scatter_timer <= 0:
            for g in self.ghosts:
                if g.mode != "frightened":
                    g.mode = "scatter" if g.mode=="chase" else "chase"
            self.scatter_timer = FPS * 7
        # update ghosts
        for g in self.ghosts:
            g.update(self.maze,self.pacman,self.ghosts,self.preset)
        # collisions
        for g in self.ghosts:
            if not g.alive: continue
            if (g.x,g.y) == (self.pacman.x,self.pacman.y):
                if g.mode == "frightened":
                    g.alive = False
                    g.respawn_timer = FPS*4
                    self.pacman.score += 200
                else:
                    self.pacman.lives -= 1
                    if self.pacman.lives <= 0:
                        self.message = "GAME OVER - PRESS SPACE TO RESTART"
                    else:
                        self.message = f"Lives left: {self.pacman.lives}"
                        # reset positions
                        self.pacman.x,self.pacman.y = 14,23
                        for gg in self.ghosts: gg.reset()
                    return
        # level complete?
        if not self.maze.pellets and not self.maze.power:
            self.level += 1
            self.maze_idx = (self.maze_idx + 1) % len(MAZE_VARIANTS)
            self.reset_level()

    def draw(self,surf):
        surf.fill((0,0,0))
        self.maze.draw(surf)
        self.pacman.draw(surf)
        for g in self.ghosts:
            g.draw(surf)
        # HUD
        hud = font.render(f"Score: {self.pacman.score}  Lives: {self.pacman.lives}  Level: {self.level}  Difficulty: {self.diff}", True, (220,220,220))
        surf.blit(hud, (6, GRID_H*TILE+4))
        if self.message:
            msg = font.render(self.message, True, (255,200,0))
            surf.blit(msg, (SCREEN_W//2 - msg.get_width()//2, 2))

# ----- Input handling -----
def handle_events(game):
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if ev.key == pygame.K_UP:
                game.pacman.set_dir((0,-1))
            if ev.key == pygame.K_DOWN:
                game.pacman.set_dir((0,1))
            if ev.key == pygame.K_LEFT:
                game.pacman.set_dir((-1,0))
            if ev.key == pygame.K_RIGHT:
                game.pacman.set_dir((1,0))
            if ev.key == pygame.K_d:
                game.change_difficulty()
            if ev.key == pygame.K_m:
                game.change_maze()
            if ev.key == pygame.K_r:
                game.reset_level()
            if ev.key == pygame.K_SPACE:
                # restart full game
                game.__init__()

# ----- Main loop -----
# small helper to map DIFFICULTY_PRESETS usage in earlier Pacman update
DIFIC = DIFFICULTY  # will be set correctly in Game init, but for pacman update usage we set global ref
def main():
    global DIFIC
    game = Game()
    DIFIC = game.diff
    splash = FPS*2
    while True:
        handle_events(game)
        # keep global DIFIC in sync for pacman power time reference
        DIFIC = game.diff
        if splash > 0:
            splash -= 1
        else:
            game.update()
        game.draw(screen)
        help_text = font.render("Arrows: move   D: change difficulty   M: change maze   R: reset   SPACE: restart", True, (180,180,180))
        screen.blit(help_text, (6, GRID_H*TILE+4+18))
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()

