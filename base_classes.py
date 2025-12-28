import math
import arcade
import arcade.gl

sprite_all_draw = arcade.SpriteList()

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
    def __init__(self, pos: Vec2, size: Vec2, color: tuple[float, float, float], ctx):
        self.pos = pos
        self.size = size
        self.angle = 0
        # self.rect: arcade.rect.Rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        self.rect: arcade.Sprite = arcade.SpriteSolidColor(self.size.x, self.size.y, self.pos.x, self.pos.y, color, self.angle)
        sprite_all_draw.append(self.rect)
        self.velocity: Vec2 = Vec2(0.0, 0.0)
        self.color = color
    # def draw(self):
        # arcade.draw_rect_filled(self.rect, self.color, self.angle)
    
    def update(self, dt: float):
        self.pos += self.velocity*dt
        # self.rect = arcade.rect.XYWH(self.pos.x, self.pos.y, self.size.x, self.size.y)
        self.rect.center_x= self.pos.x
        self.rect.center_y= self.pos.y
        self.rect.angle = self.angle
    
    def die(self):
        sprite_all_draw.remove(self.rect)

    def update_vel(self, vel: Vec2, max_vel: float= 1.0):
        nv = self.velocity + vel
        if math.sqrt(nv.x**2+nv.y**2) <= max_vel:
            self.velocity = nv
    def collide(self, other: Entity):
        return bool(self.rect.rect.intersection(other.rect.rect))

class Bar:
    def __init__(self, pos: Vec2, size: Vec2, color, bg_color, value, max_value, ctx):
        self.pos = pos
        self.size = size
        self.color = color
        self.bg_color = bg_color
        self.value = value
        self.max_value = max_value
        self.background_rect = Rect(self.pos, self.size, ctx)
        self.front_rect = Rect(self.pos, self.size, ctx)
        self.text_pos = Vec2(
            (pos.x+size.x+1)/2*1920,
            (pos.y+1)/2*1080,
        )
        bg_sh = """
            #version 330
            out vec4 fragColor;
            uniform vec3 color;
            void main()
            {
                vec3 col = color / 255.0;
                fragColor = vec4(col, 1.0);
            }
        """

        fr_sh = """
            #version 330
            out vec4 fragColor;
            uniform vec3 color;
            uniform float progress;
            void main()
            {
                vec3 col = color / 255.0;
                float p = progress * 2.0 - 1.0;
                float alpha = 0.0;
                if (fragColor.x <= p){
                    alpha = 1.0;
                } else{
                    alpha = 0.0;
                }
                fragColor = vec4(col, alpha);
            }
        """
        self.background_rect.frag = bg_sh
        self.front_rect.frag = fr_sh
        self.background_rect.update_program()
        self.front_rect.update_program()

    def draw(self):
        self.background_rect['color'] = self.bg_color
        self.background_rect.draw()
        self.front_rect.draw()
        arcade.draw_text(f"{self.value}/{self.max_value}", self.text_pos.x, self.text_pos.y)

