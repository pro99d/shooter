import math
import arcade
import arcade.gl

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
        self.rect: arcade.rect.Rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        self.velocity: Vec2 = Vec2(0.0, 0.0)
        self.color = color
    
    def draw(self):
        arcade.draw_rect_filled(self.rect, self.color, self.angle)
    
    def update(self, dt: float):
        self.pos += self.velocity*dt
        self.rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)

    def update_vel(self, vel: Vec2, max_vel: float= 1.0):
        nv = self.velocity + vel
        if math.sqrt(nv.x**2+nv.y**2) <= max_vel:
            self.velocity = nv
    def collide(self, other: Entity):
        return bool(self.rect.intersection(other.rect))
