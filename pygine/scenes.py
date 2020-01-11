import pygame
from enum import IntEnum
from pygame import Rect
from pygine.entities import *
from pygine.input import InputType, pressed
from pygine.maths import Vector2
from pygine.structures import Quadtree, Bin
from pygine.transitions import Pinhole, TransitionType
from pygine.triggers import OnButtonPressTrigger
from pygine.utilities import Camera, Timer
from random import randint


class SceneType(IntEnum):
    MENU = 0
    SELECT = 1
    BOSSA = 2
    BOSSB = 3
    FINALBOSS = 4


class SceneManager:
    def __init__(self):
        self.__reset()

    def get_scene(self, scene_type):
        return self.__all_scenes[int(scene_type)]

    def get_current_scene(self):
        return self.__current_scene

    def queue_next_scene(self, scene_type):
        if (self.start_transition):
            return

        self.__previous_scene = self.__current_scene
        self.__next_scene = self.__all_scenes[int(scene_type)]
        self.__setup_transition()

    def __reset(self):
        self.__all_scenes = []
        self.__current_scene = None
        self.__previous_scene = None
        self.__next_scene = None
        self.leave_transition = None
        self.enter_transition = None
        self.start_transition = False

        self.__initialize_scenes()
        self.__set_starting_scene(SceneType.MENU)

    def __add_scene(self, scene):
        self.__all_scenes.append(scene)
        scene.manager = self

    def __initialize_scenes(self):
        self.__all_scenes = []
        self.__add_scene(Menu())
        self.__add_scene(Select())
        self.__add_scene(BossA())
        self.__add_scene(BossB())
        self.__add_scene(FinalBoss())

    def __set_starting_scene(self, starting_scene_type):
        assert (len(self.__all_scenes) > 0), \
            "It looks like you never initialized all the scenes! Make sure to setup and call __initialize_scenes()"

        self.__current_scene = self.__all_scenes[int(starting_scene_type)]

    def __setup_transition(self):
        if self.__previous_scene.leave_transition_type == TransitionType.PINHOLE_CLOSE:
            self.leave_transition = Pinhole(TransitionType.PINHOLE_CLOSE)

        if self.__next_scene.enter_transition_type == TransitionType.PINHOLE_OPEN:
            self.enter_transition = Pinhole(TransitionType.PINHOLE_OPEN)

        self.start_transition = True

    def __change_scenes(self):
        self.__current_scene = self.__next_scene
        self.__current_scene.load_scene()

    def __update_input(self, delta_time):
        if pressed(InputType.RESET):
            self.__reset()

    def __update_transition(self, delta_time):
        if self.start_transition:
            self.leave_transition.update(delta_time)
            if self.leave_transition.done:
                self.enter_transition.update(delta_time)
                self.__change_scenes()

    def update(self, delta_time):
        assert (self.__current_scene != None), \
            "It looks like you never set a starting scene! Make sure to call __set_starting_scene(starting_scene_type)"

        self.__update_input(delta_time)
        self.__update_transition(delta_time)
        self.__current_scene.update(delta_time)

    def __draw_transitions(self, surface):
        if self.start_transition:
            if self.leave_transition != None and not self.leave_transition.done:
                self.leave_transition.draw(surface)
                if self.leave_transition.done:
                    self.enter_transition.draw(surface)
            else:
                self.enter_transition.draw(surface)
                if (self.enter_transition.done):
                    self.start_transition = False

    def draw(self, surface):
        assert (self.__current_scene != None), \
            "It looks like you never set a starting scene! Make sure to call __set_starting_scene(starting_scene_type)"

        self.__current_scene.draw(surface)
        self.__draw_transitions(surface)


class SceneDataRelay(object):
    def __init__(self):
        self.scene_bounds = None
        self.entities = None
        self.entity_quad_tree = None
        self.entity_bin = None
        self.kinetic_quad_tree = None
        self.actor = None

        self.entity_buffer = []

    def set_scene_bounds(self, bounds):
        self.scene_bounds = bounds

    def update(self, entites, entity_quad_tree, entity_bin, kinetic_quad_tree, actor):
        self.entities = entites
        self.entity_quad_tree = entity_quad_tree
        self.entity_bin = entity_bin
        self.kinetic_quad_tree = kinetic_quad_tree
        self.actor = actor


class Scene(object):
    VIEWPORT_BUFFER = 32

    def __init__(self):
        self.scene_bounds = Rect(
            0,
            0,
            Camera.BOUNDS.width,
            Camera.BOUNDS.height
        )

        self.camera = Camera()
        self.camera_location = Vector2(0, 0)
        self.camera_viewport = Rectangle(
            -Scene.VIEWPORT_BUFFER,
            -Scene.VIEWPORT_BUFFER,
            Camera.BOUNDS.width + Scene.VIEWPORT_BUFFER * 2,
            Camera.BOUNDS.height + Scene.VIEWPORT_BUFFER * 2,
            Color.RED,
            2
        )

        self.entities = []
        self.sprites = []
        self.shapes = []
        self.triggers = []

        self.sprite_quad_tree = Quadtree(self.scene_bounds, 4)
        self.shape_quad_tree = Quadtree(self.scene_bounds, 4)
        self.entity_quad_tree = Quadtree(self.scene_bounds, 4)
        self.kinetic_quad_tree = Quadtree(self.scene_bounds, 4)
        self.entity_bin = Bin(self.scene_bounds, 4)
        self.query_result = None
        self.first_pass = True
        self.entities_are_uniform = False
        self.optimal_bin_size = 0

        self.leave_transition_type = TransitionType.PINHOLE_CLOSE
        self.enter_transition_type = TransitionType.PINHOLE_OPEN
        self.manager = None
        self.actor = None

        self.scene_data = SceneDataRelay()
        self.scene_data.set_scene_bounds(self.scene_bounds)

    def setup(self, entities_are_uniform, maximum_entity_dimension=0):
        self.entities_are_uniform = entities_are_uniform
        if self.entities_are_uniform:
            self.optimal_bin_size = int(
                math.ceil(math.log(maximum_entity_dimension, 2)))

        self._reset()
        self._create_triggers()

    def set_scene_bounds(self, bounds):
        self.scene_bounds = bounds
        self.scene_data.set_scene_bounds(self.scene_bounds)

        buffer = 0
        modified_bounds = Rect(
            -buffer,
            -buffer,
            self.scene_bounds.width + buffer * 2,
            self.scene_bounds.height + buffer * 2,
        )

        self.sprite_quad_tree = Quadtree(modified_bounds, 4)
        self.shape_quad_tree = Quadtree(modified_bounds, 4)
        self.entity_quad_tree = Quadtree(modified_bounds, 4)
        self.kinetic_quad_tree = Quadtree(self.scene_bounds, 4)
        if self.entities_are_uniform:
            self.entity_bin = Bin(modified_bounds, self.optimal_bin_size)
        self.first_pass = True

    def relay_actor(self, actor):
        if actor != None:
            self.actor = actor
            self.entities.append(self.actor)

    def relay_entity(self, entity):
        self.entities.append(entity)
        # We can potentially add aditional logic for certain entites. For example, if the entity is a NPC then spawn it at (x, y)

    def _reset(self):
        raise NotImplementedError(
            "A class that inherits Scene did not implement the reset() method")

    def _create_triggers(self):
        raise NotImplementedError(
            "A class that inherits Scene did not implement the create_triggers() method")

    def __update_spatial_partitioning(self):
        if self.first_pass:
            self.sprite_quad_tree.clear()
            for i in range(len(self.sprites)):
                self.sprite_quad_tree.insert(self.sprites[i])

            self.shape_quad_tree.clear()
            for i in range(len(self.shapes)):
                self.shape_quad_tree.insert(self.shapes[i])
            self.first_pass = False

            self.entity_quad_tree.clear()
            if self.entities_are_uniform:
                self.entity_bin.clear()
            for i in range(len(self.entities)):
                if not isinstance(self.entities[i], Kinetic):
                    self.entity_quad_tree.insert(self.entities[i])
                    if self.entities_are_uniform:
                        self.entity_bin.insert(self.entities[i])

        self.kinetic_quad_tree.clear()
        for i in range(len(self.entities)):
            if isinstance(self.entities[i], Kinetic):
                self.kinetic_quad_tree.insert(self.entities[i])

    def __update_entities(self, delta_time):
        for i in range(len(self.entities)-1, -1, -1):
            self.entities[i].update(delta_time, self.scene_data)
            if self.entities[i].remove:
                del self.entities[i]

        if (len(self.scene_data.entity_buffer) > 0):
            for i in range(len(self.scene_data.entity_buffer)-1, -1, -1):
                self.entities.append(self.scene_data.entity_buffer[i])
            self.scene_data.entity_buffer = []

    def __update_triggers(self, delta_time):
        for t in self.triggers:
            t.update(delta_time, self.scene_data, self.manager)

    def __update_camera(self):
        if self.actor != None:
            self.camera_location = Vector2(
                self.actor.x + self.actor.width / 2 - self.camera.BOUNDS.width / 2,
                self.actor.y + self.actor.height / 2 - self.camera.BOUNDS.height / 2
            )

        self.camera.update(self.camera_location, self.scene_bounds)
        self.camera_viewport.set_location(
            self.camera.get_viewport_top_left().x - Scene.VIEWPORT_BUFFER,
            self.camera.get_viewport_top_left().y - Scene.VIEWPORT_BUFFER)

    def load_scene(self):
        pass

    def update(self, delta_time):
        self.__update_spatial_partitioning()
        self.scene_data.update(
            self.entities,
            self.entity_quad_tree,
            self.entity_bin,
            self.kinetic_quad_tree,
            self.actor
        )
        self.__update_entities(delta_time)
        self.__update_triggers(delta_time)
        self.__update_camera()

    def draw(self, surface):
        self.query_result = self.shape_quad_tree.query(
            self.camera_viewport.bounds)
        for s in self.query_result:
            s.draw(surface, CameraType.DYNAMIC)

        self.query_result = self.sprite_quad_tree.query(
            self.camera_viewport.bounds)
        for s in self.query_result:
            s.draw(surface, CameraType.DYNAMIC)

        self.query_result = self.entity_quad_tree.query(
            self.camera_viewport.bounds)

        for e in self.query_result:
            e.draw(surface)

        self.query_result = self.kinetic_quad_tree.query(
            self.camera_viewport.bounds)

        for e in self.query_result:
            if not isinstance(e, Actor):
                e.draw(surface)

        if self.actor != None:
            self.actor.draw(surface)

        if globals.debugging:
            self.entity_quad_tree.draw(surface)
            for t in self.triggers:
                t.draw(surface, CameraType.DYNAMIC)


class Menu(Scene):
    def __init__(self):
        super(Menu, self).__init__()
        self.setup(False)

    def _reset(self):
        self.set_scene_bounds(
            Rect(0, 0, Camera.BOUNDS.width, Camera.BOUNDS.height))

        self.entities = []

        self.sprites = [
            Sprite((self.scene_bounds.width - 144) / 2,
                   (self.scene_bounds.height - 32) / 2, SpriteType.TITLE)
        ]

        self.shapes = []

    def _create_triggers(self):
        self.triggers = [
            OnButtonPressTrigger(
                InputType.A,
                Vector2(-128, -128),
                SceneType.SELECT
            )
        ]

    def update(self, delta_time):
        super(Menu, self).update(delta_time)

    def draw(self, surface):
        super(Menu, self).draw(surface)


class Select(Scene):
    def __init__(self):
        super(Select, self).__init__()
        self.setup(False)

        # TEMP
        self.relay_actor(PlayerA(-128, -128))

    def _reset(self):
        self.set_scene_bounds(
            Rect(0, 0, Camera.BOUNDS.width, Camera.BOUNDS.height))

        self.entities = []
        self.sprites = [
            Sprite((self.scene_bounds.width - 208) / 2,
                   (self.scene_bounds.height - 32) / 4, SpriteType.SELECT),
            Sprite((self.scene_bounds.width - 32) / 2,
                   (self.scene_bounds.height - 48) / 2, SpriteType.PLAYERA),
        ]
        self.shapes = []

    def _create_triggers(self):
        self.triggers = [
            OnButtonPressTrigger(
                InputType.A,
                Vector2(-128, -128),
                SceneType.BOSSA
            )
        ]

    def update(self, delta_time):
        # TEMP
        self.actor.set_location(-128, -128)

        super(Select, self).update(delta_time)

    def draw(self, surface):
        super(Select, self).draw(surface)


class BossBattle(Scene):
    def __init__(self):
        super(BossBattle, self).__init__()
        self.setup(False)

        self.background = Sprite(0, 0, SpriteType.BACKGROUND_0)

        self.arena_setup = False
        self.player_released = False
        self.release_timer = Timer(1000)

        self.initialized = False

    def load_scene(self):
        self.initialized = False

    def _reset(self):
        self.set_scene_bounds(
            Rect(0, 0, Camera.BOUNDS.width, Camera.BOUNDS.height))
        self.entities = []
        self.sprites = []
        self.shapes = []

    def _soft_reset(self):
        self._reset_arena()
        self.player_released = False
        self.release_timer.reset()
        self.release_timer.start()

    def _create_triggers(self):
        self.triggers = []

    def _create_arena(self):
        raise NotImplementedError(
            "A class that inherits BossBattle did not implement the _create_arena() method")

    def _reset_arena(self):
        raise NotImplementedError(
            "A class that inherits BossBattle did not implement the _reset_arena() method")

    def __initialize_arena(self):
        if (self.initialized):
            return

        if (not self.arena_setup):
            self._create_arena()
            self.arena_setup = True
            self.release_timer.start()
        else:
            self._soft_reset()

        self.initialized = True

    def update(self, delta_time):

        self.__initialize_arena()

        self.release_timer.update(delta_time)
        if (not self.player_released and self.release_timer.done):
            self.actor.enter_arena()
            self.player_released = True

        if (self.actor.dead and self.actor.y > self.scene_bounds.height + 16):
            self._soft_reset()

        super(BossBattle, self).update(delta_time)

    def draw(self, surface):
        self.background.draw(surface, CameraType.STATIC)
        super(BossBattle, self).draw(surface)


class BossA(BossBattle):
    def __init__(self):
        super(BossA, self).__init__()
        self.background.set_sprite(SpriteType.BACKGROUND_0)
        self.release_timer = Timer(500)
        self.octopus = Octopus()

    def _create_arena(self):
        self.entities.append(
            Block(0, self.scene_bounds.height -
                  32, self.scene_bounds.width, 32)
        )

        self.entities.append(self.octopus)

        self.actor.set_location(
            (self.scene_bounds.width - self.actor.width / 2) / 2,
            -128
        )

    def _reset_arena(self):
        self.actor.reset()
        self.octopus.reset()

        self.actor.set_location(
            (self.scene_bounds.width - self.actor.width / 2) / 2,
            -128
        )

    def update(self, delta_time):
        if (self.octopus.dead):
            self.manager.queue_next_scene(SceneType.MENU)

        super(BossA, self).update(delta_time)

    def draw(self, surface):
        super(BossA, self).draw(surface)


class BossB(BossBattle):
    def __init__(self):
        super(BossB, self).__init__()
        self.background.set_sprite(SpriteType.BACKGROUND_1)

    def _create_arena(self):
        self.entities.append(
            Block(0, self.scene_bounds.height -
                  32, self.scene_bounds.width, 32)
        )

        self.entities.append(Golem())

        self.actor.set_location(
            (self.scene_bounds.width - self.actor.width / 2) / 2,
            -128
        )

    def update(self, delta_time):
        super(BossB, self).update(delta_time)

    def draw(self, surface):
        super(BossB, self).draw(surface)


class FinalBoss(BossBattle):
    def __init__(self):
        super(FinalBoss, self).__init__()
        self.background.set_sprite(SpriteType.BACKGROUND_2)

    def _create_arena(self):
        self.entities.append(
            Block(0, self.scene_bounds.height -
                  32, self.scene_bounds.width, 32)
        )

    def update(self, delta_time):
        super(FinalBoss, self).update(delta_time)

    def draw(self, surface):
        super(FinalBoss, self).draw(surface)
