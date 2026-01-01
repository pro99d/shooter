import math
import json
import asyncio
import functools
import arcade
import arcade.gl

sprite_all_draw = arcade.SpriteList()
waiting_list: list[arcade.SpriteSolidColor] = []
def async_func():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args):
            return await func(*args)
        return wrapped
    return wrapper

class SoundPlayer:
    def __init__(self):
        # output = Output()
        # self.stream = FileStream(file="example.mp3")
        # self.stream.play()
        # self.stream.free()
        self.select = arcade.load_sound("./assets/sounds/JDSherbert/select.wav")
        self.shot = arcade.load_sound("./assets/sounds/JDSherbert/shot.wav")
        self.explode = arcade.load_sound("./assets/sounds/JDSherbert/explode.wav")
        self.dash = arcade.load_sound("./assets/sounds/JDSherbert/dash.wav")


class Vec2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
    def dict(self):
        return {"x":self.x, "y":self.y}

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
    def __list__(self):
        return [self.x, self.y]

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
    def __setitem__(self, key, val):
        self.prog[key] = val

    def update_pos(self, pos: Vec2):
        self.quad = arcade.gl.geometry.quad_2d(
            size=(self.size.x, self.size.y), pos=(pos.x, pos.y))

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
    def __init__(self, pos: Vec2, size: Vec2, color: tuple[float, float, float]):
        self.pos = pos
        self.size = size
        self.angle = 0
        # self.rect: arcade.rect.Rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        # if len(waiting_list) > 0:
        #     self.rect = waiting_list.pop(0)
        #     self.rect.center_x = pos.x
        #     self.rect.center_y = pos.y
        #     self.rect.size = size.__list__()
        #     self.rect.angle = self.angle
        #     self.rect.color = color
        #     self.rect.rect.resize(size.x, size.y)
        # else:
        self.rect: arcade.Sprite = arcade.SpriteSolidColor(self.size.x, self.size.y, self.pos.x, self.pos.y, color, self.angle)
        sprite_all_draw.append(self.rect)
        self.velocity: Vec2 = Vec2(0.0, 0.0)
        self.color = color
        self.sounds = SoundPlayer()
    # def draw(self):
        # arcade.draw_rect_filled(self.rect, self.color, self.angle)
    
    def update(self, dt: float):
        self.pos += self.velocity*dt
        # self.rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        self.rect.center_x= self.pos.x
        self.rect.center_y= self.pos.y
        self.rect.angle = self.angle
    
    def die(self):
        if self.rect in sprite_all_draw:
            self.rect.center_y = -1000
            self.rect.center_x = -1000
            # waiting_list.append(self.rect)
            sprite_all_draw.remove(self.rect)

    def update_vel(self, vel: Vec2, max_vel: float= 1.0):
        nv = self.velocity + vel
        if math.sqrt(nv.x**2+nv.y**2) <= max_vel:
            self.velocity = nv
    def collide(self, other: Entity):
        return bool(self.rect.rect.intersection(other.rect.rect))
    def to_json(self):
        data = {
            "pos": self.pos.dict(),
            "size": self.size.dict(),
            "color": self.color,
            "velocity": self.velocity.dict(),
            "angle": self.angle
        }
        # return json.dumps(
            # data,
            # sort_keys=True,
            # indent=4)
        return data
    def from_json(self, d):
        data = json.loads(d)
        self.angle = data['angle']
        v = data['velocity']
        p = data['pos']
        s = data['size']
        self.velocity = Vec2(v['x'], v['y'])
        self.size = Vec2(s['x'], s['y'])
        self.pos = Vec2(p['x'], p['y'])
        self.color = data['color']
        self.rect.center_x= self.pos.x
        self.rect.center_y= self.pos.y
        self.rect.angle = self.angle



class Bar:
    def __init__(self, pos: Vec2, size: Vec2, color, bg_color, value, max_value):
        self.pos = pos
        self.size = size
        self.color = color
        self.bg_color = bg_color
        self.value = value
        self.max_value = max_value
        self.text_pos = Vec2(
            pos.x + size.x/2,
            pos.y,
        )

    def draw(self):
        arcade.draw_lbwh_rectangle_filled(self.pos.x, self.pos.y, self.size.x, self.size.y, self.bg_color)
        arcade.draw_lbwh_rectangle_filled(self.pos.x, self.pos.y, self.size.x*self.value/self.max_value, self.size.y, self.color)
        arcade.draw_text(f"{round(self.value, 2)}/{round(self.max_value, 2)}", self.text_pos.x, self.text_pos.y)

if __name__ == "__main__":
    e = Entity(Vec2(0, 0), Vec2(1, 1), [0, 0, 0])
    js = e.to_json()
    e.angle = 1.0
    e.pos = Vec2(1, 2)
    e.size = Vec2(2, 3)
    e.color = [1, 2, 3]
    e.velocity = Vec2(2, 4)
    e.from_json(js) 
    print(e.to_json())
