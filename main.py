import os
import random
import arcade
import arcade.gl
import time
from arcade.experimental.postprocessing import BloomEffect
from base_classes import Vec2, Rect, Entity, sprite_all_draw, Bar
import math

from arcade.gui import UIManager, UIFlatButton, UIGridLayout, UIAnchorLayout

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Arcade shooter"
enemies = []
players = []
player_alive = True
enemy_hp = 10
enemy_shot = {
    "bullets": 1,
    "reload": 1,
    "damage": 10,
    "scatter": 15,
}
# bullet_draw_rects = arcade.SpriteList()
def normalize(pos: Vec2) -> Vec2:
    pos.x -= SCREEN_WIDTH/2
    pos.y -= SCREEN_HEIGHT/2
    pos.x /= SCREEN_WIDTH/2
    pos.y /= SCREEN_HEIGHT/2
    return pos
player_pos = Vec2(0, 0)
sprite_all_draw.clear()


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
            "scatter": 15, # degrees
            "reload": 0.5,
            "lifetime": 2,
            "damage": 10
        }
        self.last_shot = 0
        self.bullets = []
        self.velocity: Vec2 = Vec2(0, 0)
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.level = 1
        self.inv = False
        self.stamina = 3
        self.stamina_max = 3
        self.last_dash = 0

    def dash(self):
        if self.stamina >= self.stamina_max:
            self.velocity *= 5
            self.stamina = 0
            self.last_dash = time.time()
    
    def shoot(self):
        if time.time()-self.last_shot >= self.shoot_prop["reload"]:
            s = self.shoot_prop["scatter"]/2
            lftime = self.shoot_prop["lifetime"]
            for _ in range(self.shoot_prop["bullets"]):
                self.bullets.append(
                    Bullet(self.pos, Vec2(10, 20), 1000, self.angle+random.uniform(-s, s), self.shoot_prop["damage"], lftime, self.ctx)
                )
            self.last_shot = time.time()

    def update(self, dt):
        self.velocity *= 0.95
        super().update(dt)
        ns = self.stamina + dt
        if ns > self.stamina_max:
            self.stamina = self.stamina_max
        else:
            self.stamina = ns
        for bul in self.bullets:
            if bul.update(dt, self.enemies):
                bul.die()
                self.bullets.remove(bul)
            if bul.lifetime>bul.max_lfetime and bul in self.bullets:
                bul.die()
                self.bullets.remove(bul)
        self.max_health = 100*(self.level**2/10+1)
        if time.time()- self.last_dash <= 0.3:
            self.inv = True
        else:
            self.inv = False

    # def draw(self):
        # super().draw()
        # for bul in self.bullets:
            # bul.draw()

class Enemy(Player):
    def __init__(self, pos: Vec2, ctx):
        global enemy_shot
        super().__init__(pos, Vec2(50, 50), players, ctx)
        self.rect.color = (50, 130, 0)
        self.health = enemy_hp 
        self.shoot_prop.update(enemy_shot)
    def calculate_new_pos(self, bul_speed, pos, e_speed):
        dist = math.dist([self.pos.x, self.pos.y], [player_pos.x, player_pos.y])
        tim = dist/bul_speed
        np = e_speed*tim + pos
        return np

    def update(self, dt):
        global enemy_hp
        dp = self.pos-self.calculate_new_pos(
            bul_speed= 1000,
            pos= player_pos,
            e_speed= players[-1].velocity
        )

        self.angle = math.degrees(math.atan2(dp.x, dp.y))

        dp = self.pos-player_pos
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
        if self.health <= 0:
            for bul in self.bullets:
                bul.die()
            self.die()
            enemies.remove(self)
            players[-1].score += 1
            enemy_hp = 5*(players[-1].score+2)
            
class Window(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT,
                         SCREEN_TITLE, resizable=False, gl_version=(4, 3), fullscreen= True)
        self.ar = self.width/self.height
        self.total_time = 0.0
        self.bloom = BloomEffect(size=(self.width, self.height))
        self.player = Player(
            pos=Vec2(x=self.width/2, y=self.height/2),
            size=Vec2(50, 50),
            enemies= enemies,
            ctx=self.ctx
        )
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((self.width, self.height))]
        )
        self.setup()
        
        self.keys = set()
        self.mouse_pos = Vec2(0, 0)
        self.shoot = False
        p = self.player.pos
        self.cam = arcade.Camera2D(position = [p.x, p.y])
        self.last_enemy_spawn = 0
        players.append(self.player)

        self.card_picker_ui: UIManager = UIManager()
        self.card_picker_ui.enable()
        self.pause_text = arcade.Text("Pause.", self.width/2, self.height*3/4,font_size= 20)
        self.restart_text = arcade.Text("Press R to restart.", self.width/2, self.height*2/4,font_size= 20)
        size = Vec2(400, 10)
        size.x /= self.width
        size.y /= self.height
        self.stamina_bar = Bar(Vec2(0, -0.8), size, (0, 240, 240), (10, 10, 10), 3, 3, self.ctx)

    def setup(self):
        global enemy_shot, player_alive, enemies, players, enemy_hp, sprite_all_draw
        sprite_all_draw.clear()
        self.enemy_delay = 2
        player_alive = True
        self.total_time = 0
        self.player = Player(
            pos=Vec2(x=self.width/2, y=self.height/2),
            size=Vec2(50, 50),
            enemies= enemies,
            ctx=self.ctx
        )

        self.upgrade_cost = 1
        self.pause = True
        enemies.clear()
        enemy_hp = 10
        players.clear()
        players.append(self.player)

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

        @but2.event("on_click")
        def up2(*_):
            self.player.shoot_prop[acts[1]["item"]]*=acts[1]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade()
            enemy_shot[en_up['item']] *= en_up['value']

        @but3.event("on_click")
        def up3(*_):
            self.player.shoot_prop[acts[2]["item"]]*=acts[2]['value']
            self.card_picker_ui.clear()
            self.pause = False
            en_up = self.generate_upgrade()
            enemy_shot[en_up['item']] *= en_up['value']

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
        global player_pos
        if player_alive:
            self.player_move()

            if self.player.health < self.player.max_health:
                self.player.health += self.player.max_health/30*dt
            else:
                self.player.health = self.player.max_health

        self.player.update(dt)
        if self.shoot and player_alive:
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

    def update_enemy(self, dt):
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

    def on_update(self, dt: float):
        global player_alive
        global player_pos
        if self.player.score != 0:
            self.enemy_delay = 1/math.sqrt(self.total_time/30)
        if self.player.score >= self.upgrade_cost:
            self.generate_upgrade_menu()
            self.upgrade_cost = 1.5*self.player.score
            self.player.level += 1
        if self.pause:
            return
        
        self.update_player(dt)
        self.update_enemy(dt)

        self.total_time += dt
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
        
        self.stamina_bar.value = self.player.stamina
        self.stamina_bar.draw()

        arcade.draw_text(f"Health: {round(self.player.health)}/{round(self.player.max_health)}", 10, 10)
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
        global player_alive
        if symbol == arcade.key.SPACE:
            self.player.dash()
        elif symbol == arcade.key.R and not player_alive:
            self.setup()


        elif symbol == arcade.key.Q:
            arcade.close_window()
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
