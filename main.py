import os
import arcade
import arcade.gl
from arcade.experimental.postprocessing import BloomEffect
import math

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Arcade shooter"


class Vec2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __add__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x+other.x, self.y+other.y)
        elif type(other) in [int, float]:
            return Vec2(self.x+other, self.y+other)

    def __mul__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x*other.x, self.y*other.y)
        elif type(other) in [int, float]:
            return Vec2(self.x*other, self.y*other)

class Rect:
    def __init__(self, pos: Vec2, size: Vec2, color, ctx):
        self.pos = pos
        self.ctx = ctx
        self.size = size
        self.color = color
        self.frag = """
            #version 330
            out vec4 fragColor;
            uniform vec3 color;
            void main()
            {
                fragColor = vec4(color, 1.0);
            }
        """
        self.quad = arcade.gl.geometry.quad_2d(
            size=(size.x, size.y), pos=(pos.x, pos.y))
        self.update_program()
        self.prog['color'] = color
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
    def __init__(self, pos: Vec2, size: Vec2, color, mass: float, ctx):
        self.pos = pos
        self.size = size
        self.color = color
        self.velocity = Vec2(0, 0)
        self.ctx = ctx
        self.mass = mass
        self.draw_rect = Rect(pos, size, color, ctx)
    
    def change_v(self, velocity: Vec2, max_vel: float=1):
        nv = self.velocity+velocity
        if math.sqrt(nv.x**2+nv.y**2) <= max_vel:
            self.velocity = nv
    
    def update(self, dt: float):
        self.pos += self.velocity*dt
        self.draw_rect.update_pos(self.pos) 
    
    def draw(self):
        self.draw_rect.draw()

class Player(Entity):
    def __init__(self, pos: Vec2, size: Vec2, ctx):
        self.ctx = ctx
        super().__init__(pos, size, (0.0, 1.0, 0.0), 1, ctx) 
    def update(self, dt):
        self.velocity*=0.95
        super().update(dt)

class Window(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT,
                         SCREEN_TITLE, resizable=True, gl_version=(4, 3))
        self.ar = self.width/self.height
        self.total_time = 0.0
        self.bloom = BloomEffect(
            size=(self.width, self.height),
        )
        self.player = Entity(
            pos= self.normalize(Vec2(100, 100)),
            size= self.normalize_size(Vec2(100, 100)),
            color= (0.0, 1.0, 0.0),
            mass= 1.0,
            ctx= self.ctx
        )
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((self.width, self.height))]
        )
        self.keys = []
    def on_resize(self, w, h):
        self.ar = w/h
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((w, h))]
        )
    def on_update(self, dt: float):
        self.total_time += dt


    def normalize(self, pos: Vec2) -> Vec2:
        pos.x -= self.width/2
        pos.y -= self.height/2
        pos.x /= self.width/2
        pos.y /= self.height/2
        return pos

    def normalize_size(self, size: Vec2) -> Vec2:
        size.x /= self.width
        size.y /= self.height

        return size
    def on_update(self, dt: float):
        self.total_time += dt
        
        dv = Vec2(0, 0)
        if arcade.key.W in self.keys:
            dv+=Vec2(0.0, 0.1)
        if arcade.key.A in self.keys:
            dv+=Vec2(-0.1, 0)
        if arcade.key.S in self.keys:
            dv+=Vec2(0.0, -0.1)
        if arcade.key.D in self.keys:
            dv+=Vec2(0.1, 0)
        self.player.change_v(dv, 2)
        self.player.update(dt, 0.95)

    def on_draw(self):
        self.fbo.use()
        self.fbo.clear()
        self.clear()

        self.player.draw()

        self.ctx.screen.use()
        self.bloom.render(source= self.fbo.color_attachments[0], target=self.ctx.screen)
    def on_mouse_drag(self, x, y, *args, **kargs):
        pos = self.normalize(Vec2(x, y))
        # self.rect_test.update_pos(pos)

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.Q:
            arcade.close_window()
        else:
            self.keys.append(symbol)
    def on_key_release(self, symbol, *args, **kargs):
        self.keys.remove(symbol)


def main():
    Window()
    arcade.run()


if __name__ == "__main__":
    main()
