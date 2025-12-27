import os
import random
import arcade
import arcade.gl
import time
from arcade.experimental.postprocessing import BloomEffect
from base_classes import Vec2, Rect, Entity
import math

from arcade.gui import UIManager, UIFlatButton, UIGridLayout, UIAnchorLayout

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Arcade shooter"
enemies = []
players = []
player_alive = True

def normalize(pos: Vec2) -> Vec2:
    pos.x -= SCREEN_WIDTH/2
    pos.y -= SCREEN_HEIGHT/2
    pos.x /= SCREEN_WIDTH/2
    pos.y /= SCREEN_HEIGHT/2
    return pos
player_pos = Vec2(0, 0)



class Bullet(Entity):
    def __init__(self, pos: Vec2, size: Vec2, vel: float, angle: float, damage: float, lifetime: float, ctx):
        super().__init__(
            pos= pos,
            size= size,
            color= (235, 235, 90),
            ctx= ctx
        )
        self.damage = damage
        self.angle = angle 
        angle = math.radians(-angle-90)
        self.velocity = Vec2(math.cos(angle)*vel, math.sin(angle)*vel)
        self.lifetime = 0
        self.max_lfetime = lifetime
    
    def update(self, dt, enemy: list):
        self.lifetime+=dt
        super().update(dt)
        for en in enemy:
            if self.collide(en):
                en.health -= self.damage
                return True
        return False


class Player(Entity):
    def __init__(self, pos: Vec2, size: Vec2, enemies, ctx):
        super().__init__(
            pos= pos,
            size= size,
            color= (0, 255, 0),
            ctx= ctx
        )
        self.enemies = enemies
        self.ctx = ctx
        self.mass = 1
        self.shoot_prop = {
            "bullets": 1,
            "spread": 15, # degrees
            "reload": 0.5,
            "lifetime": 0.9,
            "damage": 10
        }
        self.last_shot = 0
        self.bullets = []
        self.velocity: Vec2 = Vec2(0, 0)
        self.health = 100
        self.max_health = 100
        self.score = 0
    
    def shoot(self):
        if time.time()-self.last_shot >= self.shoot_prop["reload"]:
            s = self.shoot_prop["spread"]/2
            lftime = self.shoot_prop["lifetime"]
            for _ in range(self.shoot_prop["bullets"]):
                self.bullets.append(
                    Bullet(self.pos, Vec2(10, 20), 1000, self.angle+random.uniform(-s, s), self.shoot_prop["damage"], lftime, self.ctx)
                )
            self.last_shot = time.time()

    def update(self, dt):
        self.velocity *= 0.95
        super().update(dt)
        for bul in self.bullets:
            if bul.update(dt, self.enemies):
                self.bullets.remove(bul)
                # self.score += 1
            if bul.lifetime>bul.max_lfetime and bul in self.bullets:
                self.bullets.remove(bul)
    def draw(self):
        super().draw()
        for bul in self.bullets:
            bul.draw()

class Enemy(Player):
    def __init__(self, pos: Vec2, ctx):
        super().__init__(pos, Vec2(50, 50), players, ctx)
        self.color = (70, 140, 0)
    
        self.shoot_prop["reload"] = 1.5
        self.shoot_prop["bullets"] = 1
        self.shoot_prop["spread"] = 15
        self.shoot_prop["damage"] = 10

    def update(self, dt):
        dp = self.pos-player_pos
        self.angle = math.degrees(math.atan2(dp.x, dp.y))
        if self.health <= 0:
            enemies.remove(self)
            self.enemies[0].score += 1
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
            
class Window(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT,
                         SCREEN_TITLE, resizable=True, gl_version=(4, 3))
        self.ar = self.width/self.height
        self.total_time = 0.0
        self.bloom = BloomEffect(size=(self.width, self.height))
        self.player = Player(
            pos=Vec2(x=100, y=100),
            size=Vec2(50, 50),
            enemies= enemies,
            ctx=self.ctx
        )
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((self.width, self.height))]
        )
        self.keys = set()
        self.mouse_pos = Vec2(0, 0)
        self.shoot = False
        p = self.player.pos
        self.cam = arcade.Camera2D(position = [p.x, p.y])
        self.last_enemy_spawn = 0
        self.enemy_delay = 2
        players.append(self.player)
        self.upgrade_cost = 1
        self.pause = False

        self.card_picker_ui: UIManager = UIManager()
        self.card_picker_ui.enable()

    def generate_upgrade_menu(self):
        self.card_picker_ui.clear()
        self.pause = True
        anchor_layout = UIAnchorLayout()
        self.card_picker_ui.add(anchor_layout)

        acts = [self.generate_upgrade() for _ in range(3)]
        button_width = self.width // 4  # 1/4 of screen width
        but1 = UIFlatButton(text= f"improve {acts[0]['item']}\n by {(acts[0]['value']-1)*100}%", width=button_width, height=50, multiline= True)
        but2 = UIFlatButton(text= f"improve {acts[1]['item']}\n by {(acts[1]['value']-1)*100}%", width=button_width, height=50, multiline= True)
        but3 = UIFlatButton(text= f"improve {acts[2]['item']}\n by {(acts[2]['value']-1)*100}%", width=button_width, height=50, multiline= True)

        but1.place_text(anchor_x= "center", anchor_y="center")  # Center the text
        but2.place_text(anchor_x= "center", anchor_y="center")
        but3.place_text(anchor_x= "center", anchor_y="center")

        # Add buttons to anchor layout with vertical spacing
        # Position buttons with vertical spacing in the center
        anchor_layout.add(but1, anchor_x="center", anchor_y="center", align_y=100)  # Top button
        anchor_layout.add(but2, anchor_x="center", anchor_y="center")               # Middle button
        anchor_layout.add(but3, anchor_x="center", anchor_y="center", align_y=-100) # Bottom button
        
        @but1.event("on_click")
        def up1(*_):
            self.player.shoot_prop[acts[0]["item"]]*=acts[0]['value']
            self.card_picker_ui.clear()
            self.pause = False

        @but2.event("on_click")
        def up2(*_):
            self.player.shoot_prop[acts[1]["item"]]*=acts[1]['value']
            self.card_picker_ui.clear()
            self.pause = False
        @but3.event("on_click")
        def up3(*_):
            self.player.shoot_prop[acts[2]["item"]]*=acts[2]['value']
            self.card_picker_ui.clear()
            self.pause = False
    def generate_upgrade(self):
        item = random.choice(["bullets", "reload", "spread", "damage"])
        if item != "spread":
            value = 1.15#random.uniform(1.05, 1.20)
        if item == "bullets":
            value = 2
        else:
            value = random.uniform(0.9, 1.10)
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

    def on_update(self, dt: float):
        global player_alive
        global player_pos

        if self.player.score >= self.upgrade_cost:
            self.generate_upgrade_menu()
            self.upgrade_cost *= 2
        if self.pause:
            return
        self.total_time += dt
        if player_alive:
            self.player_move()
        
        self.player.update(dt)
        if self.shoot and player_alive:
            self.player.shoot()
        p = self.player.pos
        self.cam.position = [p.x, p.y]
        if p.x < 0:
            p.x = 0 
        if p.x > self.width:
            p.x = self.width

        if p.y < 0:
            p.y = 0 
        if p.y > self.height:
            p.y = self.height
        player_pos = p
        if time.time() - self.last_enemy_spawn >= self.enemy_delay and player_alive:
            pos = Vec2(
                random.randint(0, self.width),
                random.randint(0, self.height)
            )

            enemies.append(
                Enemy(pos, self.ctx)
            )
            self.last_enemy_spawn = time.time()
        for enemy in enemies:
            enemy.update(dt)
        if self.player.health <= 0:
            player_alive = False
    def on_draw(self):
        # self.cam.use()
        self.fbo.use()
        self.fbo.clear()
        self.clear()
        self.player.draw()
        for en in enemies:
            en.draw()
        self.ctx.screen.use()
        self.bloom.render(source= self.fbo.color_attachments[0], target=self.ctx.screen)
        
        arcade.draw_text(f"Health: {self.player.health}/{self.player.max_health}", 10, 10)
        arcade.draw_text(f"Score: {self.player.score}", 10, self.height-15)
        self.card_picker_ui.draw()
    
    def on_mouse_motion(self, x, y, *args, **kargs):
        self.mouse_pos = Vec2(x, y)
    
    def on_mouse_press(self, *args):
        self.shoot = True
    def on_mouse_release(self, *args):
        self.shoot = False

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.Q:
            arcade.close_window()
        else:
            self.keys.add(symbol)
    def on_key_release(self, symbol, *args):
        self.keys.remove(symbol)


def main():
    Window()
    arcade.run()


if __name__ == "__main__":
    main()
