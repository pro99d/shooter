import os
import arcade
import arcade.gl
from arcade.experimental.postprocessing import BloomEffect
import math

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Arcade shooter"


def normalize(pos: Vec2) -> Vec2:
    pos.x -= SCREEN_WIDTH/2
    pos.y -= SCREEN_HEIGHT/2
    pos.x /= SCREEN_WIDTH/2
    pos.y /= SCREEN_HEIGHT/2
    return pos
class Vec2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __add__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x+other.x, self.y+other.y)
        elif type(other) in [int, float]:
            return Vec2(self.x+other, self.y+other)

    def __sub__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x-other.x, self.y-other.y)
        elif type(other) in [int, float]:
            return Vec2(self.x-other, self.y-other)
    def __mul__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x*other.x, self.y*other.y)
        elif type(other) in [int, float]:
            return Vec2(self.x*other, self.y*other)
    def __repr__(self) -> str:
        return f"Vec2(x= {self.x}, y= {self.y})"

class Rect:
    def __init__(self, pos: Vec2, size: Vec2, ctx):
        self.pos = pos
        self.ctx = ctx
        self.size = size
        self.frag = """
            #version 330
            out vec4 fragColor;
            void main()
            {
                fragColor = vec4(1.0);
            }
        """
        self.quad = arcade.gl.geometry.quad_2d(
            size=(size.x, size.y), pos=(pos.x, pos.y))
        self.update_program()
        self.rotate(0)

    def update_pos(self, pos: Vec2):
        self.quad = arcade.gl.geometry.quad_2d(
            size=(self.size.x, self.size.y), pos=(pos.x, pos.y))

    def rotate(self, angle):
        angle = math.radians(angle)
        rotation_matrix = [
            math.cos(angle), -math.sin(angle), 0, 0,
            math.sin(angle), math.cos(angle), 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]
        # self.prog['rotation_matrix'] = rotation_matrix

    def update_program(self):
        self.prog = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_vert;
            void main()
            {
                gl_Position = vec4(in_vert, 0., 1);
            }

            """,

            fragment_shader=self.frag
        )

    def draw(self):
        self.quad.render(self.prog)

class Entity:
    def __init__(self, pos: Vec2, size: Vec2, color: tuple[float, float, float], ctx):
        self.pos = pos
        self.size = size
        self.angle = 0
        self.rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        self.velocity = Vec2(0.0, 0.0)
        self.color = color
    
    def draw(self):
        arcade.draw_rect_filled(self.rect, self.color, self.angle)
    
    def update(self, dt):
        self.pos += self.velocity*dt
        self.rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)

    def update_vel(self, vel: Vec2, max_vel: float= 1.0):
        nv = self.velocity + vel
        if math.sqrt(nv.x**2+nv.y**2) <= max_vel:
            self.velocity = nv

class Player(Entity):
    def __init__(self, pos: Vec2, size: Vec2, ctx):
        super().__init__(
            pos= pos,
            size= size,
            color= (0, 255, 0),
            ctx= ctx
        )
        self.mass = 1
    
    def update(self, dt):
        self.velocity *= 0.95
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
            ctx=self.ctx
        )
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((self.width, self.height))]
        )
        self.keys = set()
        self.mouse_pos = Vec2(0, 0)
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
    def on_update(self, dt: float):
        self.total_time += dt
        acc = 100
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
        self.player.angle = math.atan(dp.x/dp.y)
        self.player.update_vel(dv, acc*10)
        self.player.update(dt)

    def on_draw(self):
        self.fbo.use()
        self.fbo.clear()
        self.clear()
        self.player.draw()
        self.ctx.screen.use()
        self.bloom.render(source= self.fbo.color_attachments[0], target=self.ctx.screen)
    
    def on_mouse_motion(self, x, y, *args, **kargs):
        self.mouse_pos = Vec2(x, y)

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
