import math
import os
import random
import sys
import time
import threading
from threading import Thread
import json

import arcade
from arcade.experimental.postprocessing import BloomEffect
import arcade.gl
from arcade.gui import UIAnchorLayout, UIFlatButton, UIGridLayout, UIManager
from server_sync import Server, Client

from base_classes import Bar, Entity, Rect, Vec2, sprite_all_draw

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Arcade shooter"
enemies = []
players = []
bullets = []

player_alive = True
enemy_hp = 10
enemy_shot = {
    "bullets": 1,
    "reload": 1,
    "damage": 10,
    "scatter": 15,
}
score = 0

MUTE_WEARPON = False
MULTIPLAYER  = False
DASH = False
for arg in sys.argv:
    match arg:
        case "--multiplayer":
            MULTIPLAYER = True
        case "--enemy-dash":
            DASH = True
        case "--mute-wearpon":
            MUTE_WEARPON = True
        case "--help":
            print("aviable commands:")
            print("--help: print this message")
            print("--multiplayer: enable multiplayer (WIP)")
            print("--enemy-dash: enable enemy dash. give 2x score")
            print("--mute-wearpon: disables wearpon sounds")
            exit()

class SoundManager:
    def __init__(self, max_concurrent_sounds=20):
        self.max_concurrent_sounds = max_concurrent_sounds
        self.playing_sounds = []

    def play_sound(self, sound):
        self.clean_sounds()

        if len(self.playing_sounds) < self.max_concurrent_sounds:
            player = sound.play()
            if player:
                self.playing_sounds.append({"s": sound, "p": player})
                return player
        return None

    def clean_sounds(self):
        self.playing_sounds = [d for d in self.playing_sounds if d['p'].playing]

    def clear_all_sounds(self):
        for sound_dict in self.playing_sounds:
            try:
                sound_dict['p'].stop()
            except:
                pass
        self.playing_sounds.clear()

sound_manager = SoundManager(max_concurrent_sounds=25)

def normalize(pos: Vec2) -> Vec2:
    pos.x -= SCREEN_WIDTH/2
    pos.y -= SCREEN_HEIGHT/2
    pos.x /= SCREEN_WIDTH/2
    pos.y /= SCREEN_HEIGHT/2
    return pos
# player_pos = Vec2(0, 0)
sprite_all_draw.clear()


class Bullet(Entity):
    def __init__(self, pos: Vec2, size: Vec2, vel: float, angle: float, damage: float, lifetime: float, owner):
        if owner not in players:
            color = (235, 235, 90)
        else:
            color = (235, 155, 90)


        super().__init__(
            pos= pos,
            size= size,
            color= color
        )
        self.owner = owner
        self.damage = damage
        self.angle = angle
        angle = math.radians(-angle-90)
        self.velocity = Vec2(math.cos(angle)*vel, math.sin(angle)*vel)
        self.lifetime = 0
        self.max_lfetime = lifetime
        # bullet_draw_rects.append(self.rect)
    def get_nearest_enemy(self, enemies):
        dist = float("inf")
        e = None
        for enemy in enemies:
            d = math.dist((self.pos.x, self.pos.y), (enemy.pos.x, enemy.pos.y))
            if  d <= dist:
                dist = d
                e = enemy 
        return e
    def update(self, dt, enemies: list):
        self.lifetime+=dt
        # nearest_enemy = self.get_nearest_enemy(enemy)
        #auto aim
        # max_da = 16
        # dp = self.pos-nearest_enemy.pos
        # a = math.atan2(dp.y, dp.x)
        # self.angle = math.degrees(a)
        # a += math.radians(180)
        # v = math.dist((0, 0), self.velocity.__list__())
        # self.velocity = Vec2(math.cos(a), math.sin(a))*v

        super().update(dt)
        hit = False
        # for en in enemy:
        if self.owner in enemies:
            enemies.remove(self.owner)
        en = self.get_nearest_enemy(enemies)
        if en:
            if not en.inv:
                if math.dist(self.pos.__list__(), en.pos.__list__()) <= 60:
                    en.health -= self.damage
                    hit = True
                    # if en.health < self.damage:
                    #     h = en.health
                    #     en.health -= self.damage
                    #     self.damage -= h
                    #     return False
                    # else:
                    #     self.damage -= en.health
                    #     en.health = 0
                    # hit = True
        # bullet_draw_rects.append(self.rect)
        return hit



class Player(Entity):
    def __init__(self, pos: Vec2, size: Vec2, enemies):
        super().__init__(
            pos= pos,
            size= size,
            color= (0, 255, 0)
        )
        self.enemies = enemies
        self.shoot_prop = {
            "bullets": 1,
            "scatter": 15, # degrees
            "reload": 0.5,
            "lifetime": 2,
            "damage": 10
        }
        self.last_shot = 0
        self.bullets = []
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.level = 1
        self.inv = False
        self.stamina = 3
        self.stamina_max = 3
        self.last_dash = 0
        self.sound_play = set()
        self.w = 1920
        self.h = 1080
        self.regeneration = 20
        self.lstscore = 0

    def to_json(self):
        ed = super().to_json()
        nd = {
            "shoot_prop": self.shoot_prop,
            "last_shot": self.last_shot,
            "bullets": [bul.to_json() for bul in self.bullets],
            "inv": self.inv,
            "stamina": self.stamina
        }
    def dash(self, keys):

        dv = Vec2(0, 0)
        if arcade.key.W in keys:
            dv += Vec2(0.0, 1)
        if arcade.key.A in keys:
            dv += Vec2(-1, 0.0)
        if arcade.key.S in keys:
            dv += Vec2(0.0, -1)
        if arcade.key.D in keys:
            dv += Vec2(1, 0.0)
    
        if self.stamina >= 1:
            self.velocity = dv*4500
            self.stamina -= 1
            self.last_dash = time.time()
            return True
    
    def _create_bullet(self):
        s = self.shoot_prop["scatter"]/2
        lftime = self.shoot_prop["lifetime"]
        bullets.append(
            Bullet(self.pos, Vec2(10, 20), 1000, self.angle+random.uniform(-s, s), self.shoot_prop["damage"], lftime, self)
        )


    def shoot(self):
        if time.time()-self.last_shot >= self.shoot_prop["reload"]:
            for _ in range(self.shoot_prop["bullets"]):
                self._create_bullet()
            self.sound_play.add(self.sounds.shot)
            self.last_shot = time.time()
    
    def update_bullet(self, bullet, dt):
        if bullet.update(dt, self.enemies):
            bullet.die()
            if bullet in self.bullets:
                self.bullets.remove(bullet)
            s = True
        if bullet.lifetime>bullet.max_lfetime and bullet in self.bullets:
            bullet.die()
            self.bullets.remove(bullet)

    def update(self, dt):
        self.velocity *= 0.95
        super().update(dt)
        self.rect.color = (255-255*(max(min(self.health/self.max_health, 1), 0)), 255*(max(min(self.health/self.max_health, 1), 0)), 0)
        ns = self.stamina + dt
        if ns > self.stamina_max:
            self.stamina = self.stamina_max
        else:
            self.stamina = ns
        s = False
        # for bullet in self.bullets:
        #     self.update_bullet(bullet, dt)
        if s and not MUTE_WEARPON:
            sound_manager.play_sound(self.sounds.explode)
        if time.time()- self.last_dash <= 0.3:
            self.inv = True
        else:
            self.inv = False
        # if s:
            # self.sound_play.add(self.sounds.explode)
        if not MUTE_WEARPON:
            for sound in self.sound_play:
                sound_manager.play_sound(sound)
        self.sound_play.clear()
        if self.pos.x < 0:
            self.pos.x = 0
            self.velocity.x = 0
        elif self.pos.x > self.w:
            self.pos.x = self.w
            self.velocity.x = 0

        if self.pos.y < 0:
            self.pos.y = 0
            self.velocity.y = 0
        elif self.pos.y > self.h:
            self.pos.y = self.h
            self.velocity.y = 0
        if self.health < self.max_health:
            if self.level > self.lstscore and self.level % 5 == 0:
                self.regeneration /= 2
                self.lstscore = self.level 
            self.health += self.max_health/self.regeneration*dt
        else:
            self.health = self.max_health
    # def draw(self):
        # super().draw()
        # for bul in self.bullets:
            # bul.draw()

class Enemy(Player):
    def __init__(self, pos: Vec2):
        global enemy_shot
        super().__init__(pos, Vec2(50, 50), players)
        self.rect.color = (50, 130, 0)
        self.health = enemy_hp
        self.max_health = enemy_hp
        self.shoot_prop.update(enemy_shot)
    def calculate_new_pos(self, bul_speed, pos, e_speed):
        dist = math.dist([self.pos.x, self.pos.y], [pos.x, pos.y])
        tim = dist/bul_speed
        np = e_speed*tim + pos
        return np

    def get_nearest_player(self, players):
        dist = float("inf")
        p = None
        for player in players:
            if player == self:
                continue
            if isinstance(player, Bullet):
                if player.owner == self:
                    continue
            d = math.dist((self.pos.x, self.pos.y), (player.pos.x, player.pos.y))
            if  d <= dist:
                dist = d
                p = player
        return p
    
    def gen_keys(self):
        keys = set()
        for key in arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D:
            if random.randint(0, 1):
                keys.add(key)
        return keys

    def update(self, dt):
        global enemy_hp, score
        player = self.get_nearest_player(players)
        dp = self.pos-self.calculate_new_pos(
            bul_speed= 1000,
            pos= player.pos,
            e_speed= player.velocity
        )

        self.angle = math.degrees(math.atan2(dp.x, dp.y))
        # if random.randint(0, 100) == 0 and DASH:
        #     self.dash(self.gen_keys())
        dp = self.pos-player.pos
        r = -math.atan2(dp.x, dp.y)-math.radians(90)
        self.update_vel(
            Vec2(
                math.cos(r)*100,
                math.sin(r)*100,
            ),
            300
        )
        b = self.get_nearest_player(bullets)
        if b:
            if math.dist(self.pos.__list__(), b.pos.__list__()) < 100 and DASH and not self.inv and score > 20:
                self.dash(self.gen_keys())

        if player_alive:
            self.shoot()
        else:
            self.velocity = Vec2(0, 0)
        self.max_health = enemy_hp
        if not player_alive:
            for bul in self.bullets:
                bul.die()
            self.die()
            enemies.remove(self)
        if self.health <= 0:
            self.rect.color = [0, 0, 0]
            for bul in self.bullets:
                bul.die()
            self.die()
            if self in enemies:
                enemies.remove(self)
            if not DASH:
                score += 1
            else:
                score += 2
            enemy_hp = 7*score+1
            player.score = score
        super().update(dt)

class Syncer:
    def __init__(self, wind: Window):
        global players, enemies
        self.wind = wind
        self.multiplayer = "--multiplayer" in sys.argv
        self.ser = False
        if self.multiplayer:
            self.ip = input("enter ip (localhost): ")
            if not self.ip:
                self.ip = "localhost"
            self.port = input("enter port (8080): ")
            if not self.port:
                self.port = 8080
            else:
                self.port = int(self.port)
            while True:
                self.ser = input("server/client (server): ")
                if not self.ser:
                    self.ser = "server"
                if self.ser.lower() == "server":
                    self.ser = True
                    break
                elif self.ser.lower() == "client":
                    self.ser = False
                    break
                else:
                    print("please, enter client or server")
            if self.ser:
                self.server = Server(self.port, "udp")
                self.serv_uuid = self.server.uuid
                self.serv_thread = Thread(target= self.listen)
                self.stop_event = threading.Event()
                self.serv_thread.start()
            self.running = True
            self.client: Client = Client(self.ip, self.port, "udp")

            self.pause = False
            self.players = players.copy()
            self.enemies = enemies.copy()
            self.enemy_hp = enemy_hp
            self.enemy_shot = enemy_shot
            self.score = score
            self.player_alive = player_alive

            self.client.update(
                {
                    "pause": self.pause,
                    "players":self.players,
                    "enemies":enemies,
                    "enemy_hp":10,
                    "enemy_shot":enemy_shot,
                    "score":self.score,
                    "player_alive":self.player_alive,
                }
            )
            print(players)


    def stop_thread(self):
        if self.ser:
            self.client.clear(self.serv_uuid)
            self.stop_event.set()
            self.serv_thread.join()
    def listen(self):
        while not self.stop_event.is_set():
            self.server.listen()
    def get(self):
        global players, player_alive, enemies, enemy_hp, score
        data = self.client.get()
        players.clear()
        player_alive = data["player_alive"] or self.player_alive
        for pl in data["players"]:
            players.append(pl)
        if not self.ser:
            enemies.clear()
            for enemy in data['enemies']:
                enemies.append(enemy)
            enemy_hp = data['enemy_hp']
            enemy_shot = data['enemy_shot']
            self.pause = self.pause or data['pause']


        if data['score'] > self.score:
            self.score = data['score']
        self.wind.pause = self.pause
        score = self.score
        self.wind.player.score = self.score
        self.player_alive = player_alive

    def update(self):
        if not self.multiplayer:
            return
        else:

            self.client.update(
                {
                    "pause": self.pause,
                    "players":self.players,
                    "enemies":enemies,
                    "enemy_hp":10,
                    "enemy_shot":enemy_shot,
                    "score":self.score,
                    "player_alive":self.player_alive,
                }
            )


class Window(arcade.Window):
    def __init__(self):
        #----multiplayer------

        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT,
                         SCREEN_TITLE, resizable=False, gl_version=(4, 3), fullscreen= True)
        self.ar = self.width/self.height
        self.bloom = BloomEffect(size=(self.width, self.height))
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((self.width, self.height))]
        )
        self.setup()


        self.keys = set()
        self.mouse_pos = Vec2(0, 0)
        self.shoot = False
        p = self.player.pos
        self.cam = arcade.Camera2D(position = [p.x, p.y])
        self.last_enemy_spawn = time.time()
        # players.append(self.player)

        self.card_picker_ui: UIManager = UIManager()
        self.card_picker_ui.enable()
        self.pause_text = arcade.Text("Pause.", self.width/2, self.height*3/4,font_size= 20)
        self.restart_text = arcade.Text("Press R to restart.", self.width/2, self.height*2/4,font_size= 20)
        size = Vec2(400, 15)
        self.stamina_bar = Bar(Vec2(0, 20), size, (0, 200, 200), (30, 30, 30), 3, 3)
        self.health_bar = Bar(Vec2(0, 40), size, (200, 0, 0), (30, 30, 30), self.player.health, self.player.max_health)
        self.syncer = Syncer(self)
        if self.syncer.multiplayer:
            if self.syncer.ser:
                self.syncer.update()
                print(self.syncer.server.data)
            else:
                self.syncer.get()


    def setup(self):
        global enemy_shot, player_alive, enemies, players, enemy_hp, sprite_all_draw, score
        sprite_all_draw.clear()
        self.enemy_delay = 2
        player_alive = True
        self.total_time = 0.0
        if players:
            players.remove(self.player)
        self.player = Player(
            pos=Vec2(x=self.width/2, y=self.height/2),
            size=Vec2(50, 50),
            enemies= enemies,
        )

        self.upgrade_cost = 1
        self.pause = True
        enemies.clear()
        enemy_hp = 10
        players.append(self.player)
        score = 0
        enemy_shot = {
            "bullets": 1,
            "reload": 1,
            "damage": 10,
            "scatter": 15,
        }

    def generate_upgrade_menu(self):
        self.on_draw()
        self.card_picker_ui.clear()
        self.pause = True
        anchor_layout = UIAnchorLayout()
        self.card_picker_ui.add(anchor_layout)

        acts = [self.generate_upgrade(self.player.shoot_prop) for _ in range(3)]
        button_width = self.width // 4  # 1/4 of screen width
        but1 = UIFlatButton(text= f"improve {acts[0]['item']}\n by {round((acts[0]['value']-1)*100, 2)}%", width=button_width, height=50, multiline= True)
        but2 = UIFlatButton(text= f"improve {acts[1]['item']}\n by {round((acts[1]['value']-1)*100, 2)}%", width=button_width, height=50, multiline= True)
        but3 = UIFlatButton(text= f"improve {acts[2]['item']}\n by {round((acts[2]['value']-1)*100, 2)}%", width=button_width, height=50, multiline= True)

        but1.place_text(anchor_x= "center", anchor_y="center")
        but2.place_text(anchor_x= "center", anchor_y="center")
        but3.place_text(anchor_x= "center", anchor_y="center")

        anchor_layout.add(but1, anchor_x="center", anchor_y="center", align_y=100)
        anchor_layout.add(but2, anchor_x="center", anchor_y="center")
        anchor_layout.add(but3, anchor_x="center", anchor_y="center", align_y=-100)

        @but1.event("on_click")
        def up1(*_):
            self.player.shoot_prop[acts[0]["item"]]*=acts[0]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade(enemy_shot)
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

        @but2.event("on_click")
        def up2(*_):
            self.player.shoot_prop[acts[1]["item"]]*=acts[1]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade(enemy_shot)
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

        @but3.event("on_click")
        def up3(*_):
            self.player.shoot_prop[acts[2]["item"]]*=acts[2]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade(enemy_shot)
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

    def generate_upgrade(self, cur):
        item = ["scatter", "damage"]
        if cur['bullets'] < 16:
            item.append("bullets")
        if cur['reload'] >= 0.1:
            item.append("reload")
        item = random.choice(item)
        if item == "bullets":
            value = 2
        elif item == "reload":
            value = 0.75
        elif item == "scatter":
            value = random.uniform(0.75, 1.25)
        elif item == "damage":
            value = random.uniform(1.25, 1.5)
        return {"value":value, "item": item}

    def on_resize(self, w, h):
        self.ar = w/h
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h))]
        )
        SCREEN_HEIGHT = h
        SCREEN_WIDTH = w

    def normalize_size(self, size: Vec2) -> Vec2:
        size.x /= self.width
        size.y /= self.height
        return size

    def player_move(self):
        acc = 90
        dv = Vec2(0, 0)
        if arcade.key.W in self.keys:
            dv += Vec2(0.0, acc)
        if arcade.key.A in self.keys:
            dv += Vec2(-acc, 0.0)
        if arcade.key.S in self.keys:
            dv += Vec2(0.0, -acc)
        if arcade.key.D in self.keys:
            dv += Vec2(acc, 0.0)
        dp = self.player.pos-self.mouse_pos
        if dp.y:
            self.player.angle = math.degrees(math.atan2(dp.x, dp.y))
        else:
            self.player.angle = 180
        self.player.update_vel(dv, acc*10)
    def update_player(self, dt):
        global player_alive
        if player_alive:
            self.player_move()
            self.player.update(dt)
            if self.shoot:
                self.player.shoot()
        p = self.player.pos
        self.cam.position = [p.x, p.y]
        if p.x < 0:
            p.x = 0
            self.player.velocity.x = 0

        if p.x > self.width:
            p.x = self.width
            self.player.velocity.x = 0

        if p.y < 0:
            p.y = 0
            self.player.velocity.y = 0

        if p.y > self.height:
            p.y = self.height
            self.player.velocity.y = 0
        player_pos = p
        if self.player.health <= 0:
            player_alive = False

        self.player.max_health = 100*(self.player.level**2/10+1)
    def update_enemy(self, dt):
        if time.time() - self.last_enemy_spawn >= self.enemy_delay and player_alive:
            pos = Vec2(
                random.randint(0, self.width),
                random.randint(0, self.height)
            )

            enemies.append(
                Enemy(pos)
            )
            self.last_enemy_spawn = time.time()
        for enemy in enemies:
            enemy.update(dt)

    def update_bullet(self, bullet, dt):
        if bullet.update(dt, enemies+players):
            bullet.die()
            if bullet in bullets:
                bullets.remove(bullet)
            s = True
        if bullet.lifetime>bullet.max_lfetime and bullet in bullets:
            bullet.die()
            if bullet in bullets:
                bullets.remove(bullet)
    def on_update(self, dt: float):
        global player_alive
        if self.syncer.multiplayer:
            self.syncer.get()
        if not self.pause:
            for bullet in bullets:
                self.update_bullet(bullet, dt)
        if self.player.score != 0:
            self.enemy_delay = 1/math.sqrt(self.total_time/30)
        if self.player.score >= self.upgrade_cost:
            self.generate_upgrade_menu()
            self.upgrade_cost = 1.5*self.player.score
            self.player.level += 1
        if self.pause:
            return
        # Clean up finished sounds using the sound manager
        sound_manager.clean_sounds()

        self.update_player(dt)
        self.update_enemy(dt)

        self.total_time += dt
        if self.syncer.multiplayer:
            self.syncer.update()
    def on_draw(self):
        global player_alive
        # self.cam.use()
        self.fbo.use()
        self.fbo.clear()
        self.clear()
        sprite_all_draw.draw()
        arcade.draw_circle_outline(self.player.pos.x, self.player.pos.y, 50, arcade.color.BLUE, 1)
        self.ctx.screen.use()
        self.bloom.render(source= self.fbo.color_attachments[0], target=self.ctx.screen)


        self.health_bar.value = self.player.health
        self.health_bar.max_value = self.player.max_health
        self.health_bar.draw()
        self.stamina_bar.value = self.player.stamina
        self.stamina_bar.draw()

        # arcade.draw_text(f"Health: {round(self.player.health)}/{round(self.player.max_health)}", 10, 10)
        arcade.draw_text(f"Score: {self.player.score}", 10, self.height-15)
        arcade.draw_text(f"Upgrade cost: {round(self.upgrade_cost)}", 10, self.height-30)
        arcade.draw_text(f"Scatter: {self.player.shoot_prop['scatter']}", 10, self.height-45)
        arcade.draw_text(f"Bullet count: {self.player.shoot_prop['bullets']}", 10, self.height-60)
        arcade.draw_text(f"Damage: {self.player.shoot_prop['damage']}", 10, self.height-75)
        arcade.draw_text(f"Reload: {self.player.shoot_prop['reload']}", 10, self.height-90)
        arcade.draw_text(f"Level: {self.player.level}", 10, self.height-105)
        if self.pause:
            self.pause_text.draw()
        if not player_alive:
            self.restart_text.draw()
        self.card_picker_ui.draw()

    def on_mouse_motion(self, x, y, *args, **kargs):
        self.mouse_pos = Vec2(x, y)

    def on_mouse_press(self, *args):
        self.shoot = True
    def on_mouse_release(self, *args):
        self.shoot = False

    def on_key_press(self, symbol: int, modifiers: int):
        global player_alive
        if symbol == arcade.key.SPACE:
            if self.player.dash(self.keys):
                self.player.sounds.dash.play()
        elif symbol == arcade.key.R and not player_alive:
            self.setup()


        elif symbol == arcade.key.Q:
            arcade.close_window()
            self.syncer.stop_thread()
        elif symbol == arcade.key.P:
            self.pause = not self.pause
        if self.pause and symbol not in (arcade.key.W,arcade.key.A,arcade.key.S,arcade.key.D,arcade.key.SPACE):
            self.pause = False
        self.keys.add(symbol)
    def on_key_release(self, symbol, *args):
        if symbol in self.keys:
            self.keys.remove(symbol)
def main():
    Window()
    arcade.run()

if __name__ == "__main__":
    main()
