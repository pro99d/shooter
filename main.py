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
player_alive = True
playing_sounds = []
enemy_hp = 10
enemy_shot = {
    "bullets": 1,
    "reload": 1,
    "damage": 10,
    "scatter": 15,
}
score = 0
# bullet_draw_rects = arcade.SpriteList()
def normalize(pos: Vec2) -> Vec2:
    pos.x -= SCREEN_WIDTH/2
    pos.y -= SCREEN_HEIGHT/2
    pos.x /= SCREEN_WIDTH/2
    pos.y /= SCREEN_HEIGHT/2
    return pos
# player_pos = Vec2(0, 0)
sprite_all_draw.clear()


class Bullet(Entity):
    def __init__(self, pos: Vec2, size: Vec2, vel: float, angle: float, damage: float, lifetime: float):
        super().__init__(
            pos= pos,
            size= size,
            color= (235, 235, 90)
        )
        self.damage = damage
        self.angle = angle 
        angle = math.radians(-angle-90)
        self.velocity = Vec2(math.cos(angle)*vel, math.sin(angle)*vel)
        self.lifetime = 0
        self.max_lfetime = lifetime
        # bullet_draw_rects.append(self.rect)
    
    def update(self, dt, enemy: list):
        self.lifetime+=dt
        # bullet_draw_rects.remove(self.rect)
        super().update(dt)
        hit = False
        for en in enemy:
            if self.collide(en):
                if not en.inv:
                    en.health -= self.damage
                hit = True
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
    def to_json(self):
        ed = super().to_json()
        nd = {
            "shoot_prop": self.shoot_prop,
            "last_shot": self.last_shot,
            "bullets": [bul.to_json() for bul in self.bullets],
            "inv": self.inv,
            "stamina": self.stamina
        }
    def dash(self):
        if self.stamina >= 1:
            self.velocity *= 5
            self.stamina -= 1
            self.last_dash = time.time()
            self.sounds.dash.play()
    
    def shoot(self):
        if time.time()-self.last_shot >= self.shoot_prop["reload"]:
            s = self.shoot_prop["scatter"]/2
            lftime = self.shoot_prop["lifetime"]
            for _ in range(self.shoot_prop["bullets"]):
                self.bullets.append(
                    Bullet(self.pos, Vec2(10, 20), 1000, self.angle+random.uniform(-s, s), self.shoot_prop["damage"], lftime)
                )
            self.sound_play.add(self.sounds.shot)
            self.last_shot = time.time()

    def update(self, dt):
        global playing_sounds
        self.velocity *= 0.95
        super().update(dt)
        self.rect.color = (255-255*(max(min(self.health/self.max_health, 1), 0)), 255*(max(min(self.health/self.max_health, 1), 0)), 0)
        if self.health < self.max_health:
            self.health += self.max_health/10*dt
        else:
            self.health = self.max_health
        ns = self.stamina + dt
        if ns > self.stamina_max:
            self.stamina = self.stamina_max
        else:
            self.stamina = ns
        s = False
        for bul in self.bullets:
            if bul.update(dt, self.enemies):
                bul.die()
                if bul in self.bullets:
                    self.bullets.remove(bul)
                s = True
            if bul.lifetime>bul.max_lfetime and bul in self.bullets:
                bul.die()
                self.bullets.remove(bul)
        if time.time()- self.last_dash <= 0.3:
            self.inv = True
        else:
            self.inv = False
        if s:
            self.sound_play.add(self.sounds.explode)
        for sound in self.sound_play:
            c = sum([1 if i['s'] == sound else 0 for i in playing_sounds])
            if c < 5:
                s = sound.play()
                playing_sounds.append({"s":sound, "p":s})
        self.sound_play.clear()
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
    
    def get_nearest_player(self):
        global players
        dist = float("inf")
        p = None
        for player in players:
            d = math.dist((self.pos.x, self.pos.y), (player.pos.x, player.pos.y))
            if  d <= dist:
                dist = d
                p = player
        return p


    def update(self, dt):
        global enemy_hp, score
        player = self.get_nearest_player()
        dp = self.pos-self.calculate_new_pos(
            bul_speed= 1000,
            pos= player.pos,
            e_speed= player.velocity
        )

        self.angle = math.degrees(math.atan2(dp.x, dp.y))

        dp = self.pos-player.pos
        r = -math.atan2(dp.x, dp.y)-math.radians(90)
        self.update_vel(
            Vec2(
                math.cos(r)*100,
                math.sin(r)*100,
            ),
            300
        )

        if player_alive:
            self.shoot()
        else:
            self.velocity = Vec2(0, 0)
        super().update(dt)
        self.max_health = enemy_hp
        if self.health <= 0:
            for bul in self.bullets:
                bul.die()
            self.die()
            score += 1
            enemy_hp = 5*(score+2)
            player.score = score
            enemies.remove(self)
            
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
        self.total_time = 0.0
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
        self.total_time = 0
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
        self.card_picker_ui.clear()
        self.pause = True
        anchor_layout = UIAnchorLayout()
        self.card_picker_ui.add(anchor_layout)

        acts = [self.generate_upgrade() for _ in range(3)]
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
            en_up = self.generate_upgrade()
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

        @but2.event("on_click")
        def up2(*_):
            self.player.shoot_prop[acts[1]["item"]]*=acts[1]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade()
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

        @but3.event("on_click")
        def up3(*_):
            self.player.shoot_prop[acts[2]["item"]]*=acts[2]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade()
            enemy_shot[en_up['item']] *= en_up['value']
            self.player.sounds.select.play()

    def generate_upgrade(self):
        item = random.choice(["bullets", "reload", "scatter", "damage"])
        if item == "bullets":
            value = 2
        elif item == "reload":
            value = 0.75
        elif item == "scatter":
            value = random.uniform(0.75, 1.25)
        elif item == "damage":
            value = 1.25
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

    def on_update(self, dt: float):
        global player_alive, playing_sounds
        if self.syncer.multiplayer:
            self.syncer.get()
        if self.player.score != 0:
            self.enemy_delay = 1/math.sqrt(self.total_time/30)
        if self.player.score >= self.upgrade_cost:
            self.generate_upgrade_menu()
            self.upgrade_cost = 1.5*self.player.score
            self.player.level += 1
        if self.pause:
            return
        for d in playing_sounds:
            sound = d['p']
            if not sound.playing:
                playing_sounds.remove(d)
        
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
        global player_alive, server_running
        if symbol == arcade.key.SPACE:
            self.player.dash()
        elif symbol == arcade.key.R and not player_alive:
            self.setup()


        elif symbol == arcade.key.Q:
            arcade.close_window()
            self.syncer.stop_thread()
        elif symbol == arcade.key.P:
            self.pause = not self.pause
        self.keys.add(symbol)
    def on_key_release(self, symbol, *args):
        if symbol in self.keys:
            self.keys.remove(symbol)
def main():
    Window()
    arcade.run()

if __name__ == "__main__":
    main()
