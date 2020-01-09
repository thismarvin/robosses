from enum import IntEnum
import math
from pygame import Rect
from pygine.base import PygineObject
from pygine.draw import draw_rectangle
from pygine.geometry import Rectangle, Circle
from pygine import globals
from pygine.input import InputType, pressed, pressing
from pygine.maths import Vector2
from pygine.resource import Sprite, SpriteType
from pygine.utilities import CameraType, Color, Timer
from random import randint


class Entity(PygineObject):
    def __init__(self, x=0, y=0, width=1, height=1):
        super(Entity, self).__init__(x, y, width, height)
        self.color = Color.WHITE
        self.layer = 0
        self.remove = False
        self.__bounds_that_actually_draw_correctly = Rectangle(
            self.x, self.y, self.width, self.height, self.color, 2)

    def set_color(self, color):
        self.color = color
        self.__bounds_that_actually_draw_correctly.color = color

    def set_location(self, x, y):
        super(Entity, self).set_location(x, y)
        self.__bounds_that_actually_draw_correctly.set_location(self.x, self.y)

    def update(self, delta_time, scene_data):
        raise NotImplementedError(
            "A class that inherits Entity did not implement the update(delta_time, scene_data) method")

    def _draw_bounds(self, surface, camera_type):
        self.__bounds_that_actually_draw_correctly.draw(surface, camera_type)

    def draw(self, surface):
        raise NotImplementedError(
            "A class that inherits Entity did not implement the draw(surface) method")


class Direction(IntEnum):
    NONE = 0,
    UP = 1,
    DOWN = 2,
    LEFT = 3,
    RIGHT = 4


class Kinetic(Entity):
    def __init__(self, x, y, width, height, speed):
        super(Kinetic, self).__init__(x, y, width, height)
        self.velocity = Vector2()
        self.acceleration = Vector2()
        self.default_move_speed = speed
        self.move_speed = speed
        self.facing = Direction.NONE
        self.collision_rectangles = []
        self.collision_width = 0

        self.target = 1.0 / 60
        self.accumulator = 0

    def _update_collision_rectangles(self):
        self.collision_width = 4
        self.collision_rectangles = [
            Rect(self.x + self.collision_width, self.y - self.collision_width,
                 self.width - self.collision_width * 2, self.collision_width),
            Rect(self.x + self.collision_width, self.y + self.height, self.width -
                 self.collision_width * 2, self.collision_width),
            Rect(self.x - self.collision_width, self.y + self.collision_width,
                 self.collision_width, self.height - self.collision_width * 2),
            Rect(self.x + self.width, self.y + self.collision_width,
                 self.collision_width, self.height - self.collision_width * 2)
        ]

    def _calculate_scaled_speed(self, delta_time):
        self.move_speed = self.default_move_speed * delta_time

    def _apply_force(self, delta_time):
        # Semi-Implict Euler Integrator
        self.velocity = Vector2(
            self.velocity.x + self.acceleration.x * delta_time,
            self.velocity.y + self.acceleration.y * delta_time
        )
        self.set_location(
            self.x + self.velocity.x * delta_time,
            self.y + self.velocity.y * delta_time
        )

    def _simulate(self, elapsed_time, scene_data):
        self.accumulator += elapsed_time

        while(self.accumulator >= self.target):
            self._apply_force(self.target)
            self._collision(scene_data)

            self.accumulator -= self.target

    def _collision(self, scene_data):
        raise NotImplementedError(
            "A class that inherits Kinetic did not implement the _collision(entities, entity_quad_tree) method")

    def update(self, delta_time, scene_data):
        self._simulate(delta_time, scene_data)

    def _draw_collision_rectangles(self, surface):
        for r in self.collision_rectangles:
            draw_rectangle(
                surface,
                r,
                CameraType.DYNAMIC,
                Color.RED,
            )


class Actor(Kinetic):
    def __init__(self, x, y, width, height, speed):
        super(Actor, self).__init__(x, y, width, height, speed)

    def _update_input(self):
        raise NotImplementedError(
            "A class that inherits Actor did not implement the _update_input() method")


class Player(Actor):
    def __init__(self, x, y):
        super(Player, self).__init__(x, y, 16, 32, 90)
        self.sprite = Sprite(self.x, self.y, SpriteType.NONE)
        self.query_result = None

        self.jump_height = 16 * 5 + 4
        self.jump_duration = 0.5

        self.gravity = 2 * self.jump_height / \
            (self.jump_duration * self.jump_duration)

        self.initial_jump_velocity = self.gravity * self.jump_duration

        self.lateral_acceleration = 175
        self.friction = 150
        self.drag = 50

        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, self.gravity)

        self.grounded = False
        self.jumping = False

        self.sprite_flipped = False

        self.entered_arena = False

        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def reset(self):
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, self.gravity)

        self.grounded = False
        self.jumping = False

    def enter_arena(self):
        self.reset()
        self.entered_arena = True

    def _update_input(self):
        if pressing(InputType.LEFT) and not pressing(InputType.RIGHT):
            self.acceleration.x = -self.lateral_acceleration
            if (self.velocity.x < -self.move_speed):
                self.velocity.x = -self.move_speed

            if (self.sprite_flipped):
                self.sprite.flip_horizontally(True)
                self.sprite_flipped = False

        if pressing(InputType.RIGHT) and not pressing(InputType.LEFT):
            self.acceleration.x = self.lateral_acceleration
            if (self.velocity.x > self.move_speed):
                self.velocity.x = self.move_speed

            if (not self.sprite_flipped):
                self.sprite.flip_horizontally(True)
                self.sprite_flipped = True

        if not pressing(InputType.LEFT) and not pressing(InputType.RIGHT):
            if (self.velocity.x != 0):
                dir = -1 if self.velocity.x > 0 else 1
                if (self.grounded):
                    self.acceleration.x = self.friction * dir
                else:
                    self.acceleration.x = self.drag * dir

            if (-1 < self.velocity.x and self.velocity.x < 1):
                self.velocity.x = 0
                self.acceleration.x = 0

        if (self.grounded and not self.jumping and pressing(InputType.A)):
            self.velocity.y = -self.initial_jump_velocity
            self.jumping = True

        if (self.jumping and self.velocity.y < -self.initial_jump_velocity / 2 and not pressing(InputType.A)):
            self.velocity.y = -self.initial_jump_velocity / 2
            self.jumping = False

    def __rectanlge_collision_logic(self, entity):
        # Bottom
        if self.collision_rectangles[0].colliderect(entity.bounds) and self.velocity.y < 0:
            self.set_location(self.x, entity.bounds.bottom)
        # Top
        if self.collision_rectangles[1].colliderect(entity.bounds) and self.velocity.y > 0:
            self.set_location(self.x, entity.bounds.top - self.bounds.height)

            self.velocity.y = 0
            self.grounded = True
            self.jumping = False

        # Right
        if self.collision_rectangles[2].colliderect(entity.bounds) and self.velocity.x < 0:
            self.set_location(entity.bounds.right, self.y)
        # Left
        if self.collision_rectangles[3].colliderect(entity.bounds) and self.velocity.x > 0:
            self.set_location(entity.bounds.left - self.bounds.width, self.y)

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        self.query_result = scene_data.entity_quad_tree.query(self.area)

        self.grounded = False

        if (self.x < 0):
            self.set_location(0, self.y)
            self.velocity.x = -self.velocity.x * 0.75

        if (self.x + self.width > scene_data.scene_bounds.width):
            self.set_location(
                scene_data.scene_bounds.width - self.width, self.y)
            self.velocity.x = -self.velocity.x * 0.75

        for e in self.query_result:
            if e is self:
                continue

            if (globals.debugging):
                e.set_color(Color.RED)

            if isinstance(e, Block):
                self.__rectanlge_collision_logic(e)
                self._update_collision_rectangles()

    def update(self, delta_time, scene_data):
        if (not self.entered_arena):
            return

        self._update_input()

        super(Player, self).update(delta_time, scene_data)

    def draw(self, surface):
        if globals.debugging:
            self._draw_collision_rectangles(surface)
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.DYNAMIC,
                self.color
            )
            draw_rectangle(
                surface,
                self.area,
                CameraType.DYNAMIC,
                Color.BLACK,
                1
            )
        else:
            self.sprite.draw(surface, CameraType.DYNAMIC)


class PlayerA(Player):
    def __init__(self, x, y):
        super(PlayerA, self).__init__(x, y)
        self.sprite = Sprite(self.x - 9, self.y - 16, SpriteType.PLAYERA)
        # Character specific stuff here.

    def set_location(self, x, y):
        super(PlayerA, self).set_location(x, y)
        self.sprite.set_location(self.x - 9, self.y - 16)

    def blast_em_logic(self):
        pass

    def update(self, delta_time, scene_data):
        self.blast_em_logic()

        super(PlayerA, self).update(delta_time, scene_data)

    def draw(self, surface):
        super(PlayerA, self).draw(surface)


class Block(Entity):
    def __init__(self, x, y, width, height):
        super(Block, self).__init__(x, y, width, height)

    def update(self, delta_time, scene_data):
        pass

    def draw(self, surface):
        if globals.debugging:
            draw_rectangle(surface, self.bounds,
                           CameraType.DYNAMIC, self.color, 4)
        else:
            pass


class Boss(Entity):
    def __init__(self, x, y, width, height):
        super(Boss, self).__init__(x, y, width, height)

    def hit(self):
        pass

    def update(self, delta_time, scene_data):
        pass

    def draw(self, surface):
        pass


class Octopus(Boss):
    def __init__(self):
        super(Octopus, self).__init__(0, 0, 16, 16)
        self.sprite_left = Sprite(0, 0, SpriteType.OCTOPUS)
        self.sprite_right = Sprite(160, 0, SpriteType.OCTOPUS)
        self.sprite_right.flip_horizontally(True)

    def update(self, delta_time, scene_data):
        pass

    def draw(self, surface):
        self.sprite_left.draw(surface, CameraType.STATIC)
        self.sprite_right.draw(surface, CameraType.STATIC)

class GolemHands(Kinetic):
    def __init__(self):
        super(GolemHands, self).__init__(0, 0, 16, 16, 10)
        self.sprite_left = Sprite(0, 64, SpriteType.GOLEM_FIST)
        self.sprite_right = Sprite(320 - 96, 64, SpriteType.GOLEM_FIST)
        self.sprite_right.flip_horizontally(True)

        self.is_attacking = False
        self.__attack_time = 2500
        self.__seek_speed = 5
        self.__attack_speed = 2
        self.attack_timer = Timer(self.__attack_time, True)

        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)

        # Kinetic needs this
        self.query_result = None        
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def set_location(self, x, y):
        super(GolemHands, self).set_location(x, y)
        self.sprite_left.set_location(self.x, self.y)


    def attack(self):
        self.velocity.y += self.__attack_speed
        if (not self.is_attacking):
            pass

    def seek(self, delta_time, scene_data):
        if (scene_data.actor.x + scene_data.actor.width / 2 < self.x - self.width / 2):
            self.velocity = Vector2(self.__seek_speed, 0)
        elif (scene_data.actor.x + scene_data.actor.width / 2 > self.x - self.width / 2):
            self.velocity = Vector2(-self.__seek_speed, 0)


    def __rectanlge_collision_logic(self, entity):
        # Bottom
        if self.collision_rectangles[0].colliderect(entity.bounds) and self.velocity.y < 0:
            self.set_location(self.x, entity.bounds.bottom)
        # Top
        if self.collision_rectangles[1].colliderect(entity.bounds) and self.velocity.y > 0:
            self.set_location(self.x, entity.bounds.top - self.bounds.height)
        # Right
        if self.collision_rectangles[2].colliderect(entity.bounds) and self.velocity.x < 0:
            self.set_location(entity.bounds.right, self.y)
        # Left
        if self.collision_rectangles[3].colliderect(entity.bounds) and self.velocity.x > 0:
            self.set_location(entity.bounds.left - self.bounds.width, self.y)

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        self.query_result = scene_data.entity_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if (globals.debugging):
                e.set_color(Color.RED)


    def update(self, delta_time, scene_data):
        self.attack_timer.update(delta_time)
        if (not self.attack_timer.done):
            self.seek(delta_time, scene_data)
        #else
        
        super(GolemHands, self).update(delta_time, scene_data)

    def draw(self, surface):
        self.sprite_left.draw(surface, CameraType.STATIC)
        self.sprite_right.draw(surface, CameraType.STATIC)


class Golem(Boss):
    def __init__(self):
        super(Golem, self).__init__(0, 0, 16, 16)
        self.sprite_body_left = Sprite(80, 16, SpriteType.GOLEM_BODY)
        self.sprite_body_right = Sprite(80 + 5 * 16, 16, SpriteType.GOLEM_BODY)
        self.sprite_body_right.flip_horizontally(True)

        self.hands = GolemHands()
        
    def update(self, delta_time, scene_data):
        self.hands.update(delta_time, scene_data)

    def draw(self, surface):
        self.sprite_body_left.draw(surface, CameraType.STATIC)
        self.sprite_body_right.draw(surface, CameraType.STATIC)

        self.hands.draw(surface)
