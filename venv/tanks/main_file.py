import pygame, os, sys
from random import randrange, choice

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
size = width, height = 775, 475
screen = pygame.display.set_mode(size)
screen.fill((0, 0, 0))
walls = pygame.sprite.Group()
clock = pygame.time.Clock()
track_shoot = pygame.mixer.Sound('sounds/tank_shoot.wav')
boom_sound = pygame.mixer.Sound('sounds/boom_sound.wav')


# ============================== функции ================================
def terminate():
    pygame.quit()
    sys.exit()


def load_level(filename):
    filename = 'data/' + filename
    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]
    return level_map


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


tile_width = tile_height = 16
tile_images = {
    'wall': load_image('wall.png'),
    'b_wall': load_image('b_wall.png'),
    'house': load_image('house.png')
}


# =============================== кнопки ================================


# ================================ меню =================================
class StartButton(pygame.sprite.Sprite):
    '''Кнопка для перехода в меню выбора карты'''

    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image('start.png')
        self.rect = self.image.get_rect()
        self.rect.x = 192
        self.rect.y = 100

    def get_rect_collide(self, pos):
        return self.rect.collidepoint(pos)

    def update(self, args):
        if bool(args[0].type == pygame.MOUSEBUTTONDOWN and \
                self.rect.collidepoint(args[0].pos)):
            game_stack.clear()
            game_stack.append(OnePlayerGame())


class ExitButton(pygame.sprite.Sprite):
    '''Кнопка выхода из игры'''

    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image('exit.png')
        self.rect = self.image.get_rect()
        self.rect.x = 192
        self.rect.y = 250

    def get_rect_collide(self, pos):
        return self.rect.collidepoint(pos)

    def update(self, args):
        if bool(args[0].type == pygame.MOUSEBUTTONDOWN and \
                self.rect.collidepoint(args[0].pos)):
            terminate()


class PauseButton(pygame.sprite.Sprite):
    '''Кнопка паузы'''

    def __init__(self, *group):
        super().__init__(*group)
        self.images = {False: load_image('pause.png'), True: load_image('play.png')}
        self.image = self.images[False]
        self.rect = self.image.get_rect()
        self.rect.x = 20
        self.rect.y = 380
        self.press = False

    def update(self, args):
        if bool(args[0].type == pygame.MOUSEBUTTONDOWN and \
                self.rect.collidepoint(args[0].pos)):
            self.press = not self.press
            self.image = self.images[self.press]

    def pressed(self):
        return self.press


class StartMenu:
    '''Класс для группировки кнопок стартового меню и взаимодействия с ними'''

    def __init__(self):
        self.start_button = pygame.sprite.Group()
        StartButton(self.start_button)
        self.exit_button = pygame.sprite.Group()
        ExitButton(self.exit_button)

    def update(self, *args):
        global game_stack
        self.start_button.update(args)
        self.exit_button.update(args)

    def draw(self):
        self.start_button.draw(screen)
        self.exit_button.draw(screen)

    def update_(self):
        return


# ============================== классы для основной игры ===============================
# ----------------------------------------дом-------------------------------------------
class House(pygame.sprite.Sprite):
    '''Класс ничего не делает, но при попадании в его объект снарядом игра завершается'''

    def __init__(self, group):
        super().__init__(group)
        self.image = load_image('house.png')
        self.rect = self.image.get_rect()
        self.rect.x = 413
        self.rect.y = 409


# --------------------------------------эффекты-----------------------------------------
class Explosion(pygame.sprite.Sprite):
    '''Класс анимации взрыва. После завершения анимации самоуничтожается'''

    def __init__(self, x, y, group):
        super().__init__(group)
        self.image = load_image('boom1.png')
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.n = 0  # счетчик для анимации
        boom_sound.play()

    def update(self):
        self.n += 4
        if self.n == 20:
            self.image = load_image('boom2.png')
        elif self.n == 40:
            self.image = load_image('boom3.png')
        elif self.n == 60:
            self.kill()


class Fire(pygame.sprite.Sprite):
    '''Класс для эффекта горения танка'''

    def __init__(self, x, y, group):
        super().__init__(group)
        self.image = load_image('fire.png')
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def move(self, x, y):
        self.rect.x, self.rect.y = x, y


# ---------------------------------------снаряды----------------------------------------
class Projectile(pygame.sprite.Sprite):
    '''Основной снаряд'''

    def __init__(self, x, y, direction, target, *group):
        super().__init__(*group)
        track_shoot.play()  # звук выстрела
        self.direction = direction
        if direction == 1:
            self.vx, self.vy = 0, -5
            self.image = load_image('projectileUp.png')
        elif direction == 2:
            self.vx, self.vy = 5, 0
            self.image = load_image('projectileR.png')
        elif direction == 3:
            self.vx, self.vy = 0, 5
            self.image = load_image('projectileD.png')
        elif direction == 4:
            self.vx, self.vy = -5, 0
            self.image = load_image('projectileL.png')
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.target = target  # цель
        self.damage = randrange(40, 48)  # случайный урон
        self.second_damage = 0

    def move(self, wall_group, ex_group, house):
        # ------- обработка стен -------
        self.rect.top += self.vy
        self.rect.left += self.vx
        walls_ = pygame.sprite.spritecollide(self, wall_group, False)
        if not (walls_ is None):
            for w in walls_:
                w.kill_()
                Explosion(self.rect.x - 12, self.rect.y - 12, ex_group)
                self.kill()
        # ------ обработка выхода за поле ------
        if self.rect.top < 25:
            Explosion(self.rect.centerx - 16, 11, ex_group)
            self.kill()
        elif self.rect.top > 425:
            Explosion(self.rect.centerx - 16, 425, ex_group)
            self.kill()
        elif self.rect.left < 125:
            Explosion(111, self.rect.centery - 16, ex_group)
            self.kill()
        elif self.rect.left > 733:
            Explosion(733, self.rect.centery - 16, ex_group)
            self.kill()
        # ------ обработка попадания в дом ------
        if pygame.sprite.spritecollideany(self, house):
            game_stack.clear()
            game_stack.append(LoseMenu())

    def get_damage(self):
        # возвращение данных об уроне и позиции для взрыва
        if self.direction == 1:
            return self.damage, self.second_damage, self.rect.centerx - 16, self.rect.y + 4
        elif self.direction == 2:
            return self.damage, self.second_damage, self.rect.x + 4, self.rect.centery - 16
        elif self.direction == 3:
            return self.damage, self.second_damage, self.rect.centerx - 16, self.rect.y - 4
        elif self.direction == 4:
            return self.damage, self.second_damage, self.rect.x - 4, self.rect.centery - 16

    def get_target(self):
        return self.target


class HighExplosiveProjectile(Projectile):
    '''Огненный снаряд, наносит повторный урон 70% от основного, если, конечно, враг выжил'''

    def __init__(self, x, y, direction, target, *group):
        super().__init__(x, y, direction, target, *group)
        self.second_damage = self.damage * 0.7  # урон от горения равен 70% от основного урона
        if direction == 1:
            self.image = load_image('h_ex_projectileUp.png')
        elif direction == 2:
            self.image = load_image('h_ex_projectileR.png')
        elif direction == 3:
            self.image = load_image('h_ex_projectileD.png')
        elif direction == 4:
            self.image = load_image('h_ex_projectileL.png')


# -----------------------------------иконки снарядов------------------------------------
class HighExplosiveProjectileIcon(pygame.sprite.Sprite):
    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image('h_ex_projectile_icon.png')
        self.rect = self.image.get_rect()
        self.rect.x = 25
        self.rect.y = 100


class ProjectileIcon(pygame.sprite.Sprite):
    def __init__(self, *group):
        super().__init__(*group)
        self.image = load_image('projectile_icon.png')
        self.rect = self.image.get_rect()
        self.rect.x = 25
        self.rect.y = 100


# -----------------------------------------танки----------------------------------------
class EnemyTank(pygame.sprite.Sprite):
    '''Класс танка врага'''

    def __init__(self, coords, group):
        super().__init__(group)
        self.name = 'en'
        self.group = group
        self.im_up = load_image('en_tank.png')
        self.im_r = load_image('en_tankr.png')
        self.im_d = load_image('en_tankd.png')
        self.im_l = load_image('en_tankL.png')
        self.image = self.im_d
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = coords
        self.rotation = 3  # направление танка
        self.vx, self.vy = 0, 2

        self.hp = randrange(137, 144)
        self.second_damage = 0
        self.d2 = False
        self.d2_timer = 0
        self.shoot_timer = choice([0, 60, 120])
        self.fire = pygame.sprite.Group()
        Fire(self.rect.x, self.rect.y, self.fire)

    def new_vx(self, x):
        self.vx = x

    def new_vy(self, y):
        self.vy = y

    def move(self, *groups):
        # движение врага
        x, y = self.rect.x, self.rect.y
        # движение по последнему вектору
        self.rect.top += self.vy
        self.rect.left += self.vx
        for group in groups:
            # если враг столкнулся с чем-либо, он случайным образом меняет направление
            if pygame.sprite.spritecollideany(self, group) or self.rect.top > 409 or \
                    self.rect.top < 25 or self.rect.left > 717 or self.rect.left < 124:
                self.rect.top -= self.vy
                self.rect.left -= self.vx
                x, y, rt = choice([(0, -2, 1), (2, 0, 2), (0, 2, 3), (-2, 0, 4)])
                while rt == self.rotation:
                    x, y, rt = choice([(0, -2, 1), (2, 0, 2), (0, 2, 3), (-2, 0, 4)])
                self.vx, self.vy, self.rotation = x, y, rt
                # смена картинки
                if rt == 1:
                    self.image = self.im_up
                elif rt == 2:
                    self.image = self.im_r
                elif rt == 3:
                    self.image = self.im_d
                elif rt == 4:
                    self.image = self.im_l

    def proj_coll(self, pr_group, exp_group):
        # столкновение со снарядом
        projs = pygame.sprite.spritecollide(self, pr_group, False)
        for proj in projs:
            if proj.get_target() == self.name:
                damage, damage2, x, y = proj.get_damage()
                self.hp -= damage
                self.second_damage += damage2
                if damage2 != 0:
                    self.d2 = True
                Explosion(x, y, exp_group)
                proj.kill()

    def update(self):
        # обновление двойного урона
        if self.d2:
            self.d2_timer += 1
            for i in self.fire:
                i.move(self.rect.x, self.rect.y)
            if self.d2_timer == 120:
                self.d2_timer = 0
                self.d2 = False
                self.hp -= self.second_damage

    def shoot(self, group):
        # выстрел
        self.shoot_timer += 1
        if self.shoot_timer == 180:
            self.shoot_timer = 0
            track_shoot.play()
            if self.rotation == 1:
                Projectile(self.rect.x + 12, self.rect.y - 12, self.rotation, 'pl', group)
            elif self.rotation == 2:
                Projectile(self.rect.x + 34, self.rect.y + 12, self.rotation, 'pl', group)
            elif self.rotation == 3:
                Projectile(self.rect.x + 12, self.rect.y + 34, self.rotation, 'pl', group)
            elif self.rotation == 4:
                Projectile(self.rect.x - 12, self.rect.y + 12, self.rotation, 'pl', group)

    def update_hp(self):
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def draw_fire(self):
        # отрисовка горения
        if self.d2:
            self.fire.draw(screen)


class PlayerTank(pygame.sprite.Sprite):
    '''Класс танка игрока'''
    def __init__(self, coords, group):
        super().__init__(group)
        self.group = group
        self.name = 'pl'
        self.im_up = load_image('pl_tank.png')
        self.im_r = load_image('pl_tankR.png')
        self.im_d = load_image('pl_tankD.png')
        self.im_l = load_image('pl_tankL.png')
        self.image = self.im_up
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = coords
        self.rotation = 1
        self.vx, self.vy = 0, 0
        self.hp = 250
        self.second_damage = 0
        self.d2 = False  # чтобы не получать повторный урон сразу же
        self.d2_timer = 0
        self.pr_type = 0

    def new_vx(self, x):
        if self.vy == 0 or x == 0:
            if x < 0:
                self.rotation = 4
                self.image = self.im_l
            elif x > 0:
                self.rotation = 2
                self.image = self.im_r
            self.vx = x

    def new_vy(self, y):
        if self.vx == 0 or y == 0:
            if y < 0:
                self.rotation = 1
                self.image = self.im_up
            elif y > 0:
                self.rotation = 3
                self.image = self.im_d
            self.vy = y

    def move(self, *groups):
        # движение танка
        self.rect.top += self.vy
        self.rect.left += self.vx
        for group in groups:
            if pygame.sprite.spritecollideany(self, group) or self.rect.top > 409 or \
                    self.rect.top < 25 or self.rect.left > 717 or self.rect.left < 124:
                self.rect.top -= self.vy
                self.rect.left -= self.vx
                break

    def proj_coll(self, pr_group, exp_group):
        # столкновение со снарядами
        projs = pygame.sprite.spritecollide(self, pr_group, False)
        for proj in projs:
            if proj.get_target() == self.name:
                damage, damage2, x, y = proj.get_damage()
                self.hp -= damage
                self.second_damage += damage2
                if damage2 != 0:
                    self.d2 = True
                Explosion(x, y, exp_group)
                proj.kill()

    def update(self):
        # обновление урона от горения
        if self.d2:
            self.d2_timer += 1
            if self.d2_timer == 120:
                self.d2_timer = 0
                self.d2 = False
                self.hp -= self.second_damage

    def update_hp(self):
        # обновление здоровья
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def get_pos(self):
        # возврат данных, необходимых для выстрела
        self.pr_type += 1
        if self.pr_type == 5:
            self.pr_type = 0
        if self.rotation == 1:
            return self.rect.x + 12, self.rect.y - 12, self.pr_type, self.rotation
        elif self.rotation == 2:
            return self.rect.x + 34, self.rect.y + 12, self.pr_type, self.rotation
        elif self.rotation == 3:
            return self.rect.x + 12, self.rect.y + 34, self.pr_type, self.rotation
        elif self.rotation == 4:
            return self.rect.x - 12, self.rect.y + 12, self.pr_type, self.rotation

    def get_info(self):
        return self.hp, self.pr_type


# -----------------------------------------стены----------------------------------------
class BWall(pygame.sprite.Sprite):
    def __init__(self, x, y, group):
        super().__init__(group)
        self.image = tile_images['b_wall']
        self.rect = self.image.get_rect().move(
            tile_width * x + 125, tile_height * y + 25)

    def kill_(self):
        self.kill()


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, group):
        super().__init__(group)
        self.image = tile_images['wall']
        self.rect = self.image.get_rect().move(
            tile_width * x + 125, tile_height * y + 25)

    def kill_(self):
        return  # неразрушимая стена не может разрушиться


# --------------------------------------------------------------------------------------


class OnePlayerGame:
    '''Класс основной игры'''
    def __init__(self):
        self.walls = pygame.sprite.Group()
        self.en_tanks = pygame.sprite.Group()
        self.pl_tank = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.pause_button = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.house = pygame.sprite.Group()

        House(self.house)
        self.player_tank = PlayerTank((365, 409), self.pl_tank)
        PauseButton(self.pause_button)
        self.enemy_count = 12  # количество врагов "в запасе"
        # -------- возможные координаты новых танков --------
        self.summon_coords = [(173, 25), (413, 25), (653, 25)]
        for i in range(3):  # изначально танки появятся равномерно
            EnemyTank(self.summon_coords[i], self.en_tanks)

        # иконки снарядов
        self.h_ex_proj = pygame.sprite.Group()
        HighExplosiveProjectileIcon(self.h_ex_proj)
        self.proj = pygame.sprite.Group()
        ProjectileIcon(self.proj)

        level = load_level('map1.txt')
        for y in range(26):
            for x in range(39):
                if level[y][x] == 'b':
                    BWall(x, y, self.walls)
                elif level[y][x] == 'w':
                    Wall(x, y, self.walls)
        self.pl_shoot = True

    def draw(self):
        pygame.draw.rect(screen, (120, 120, 120), (0, 0, 125, height))
        pygame.draw.rect(screen, (120, 120, 120), (749, 0, width, height))
        pygame.draw.rect(screen, (120, 120, 120), (0, 0, width, 25))
        pygame.draw.rect(screen, (120, 120, 120), (0, 441, width, height))
        pygame.draw.rect(screen, (0, 0, 0), (12, 94, 100, 33))
        self.walls.draw(screen)
        self.pl_tank.draw(screen)
        self.en_tanks.draw(screen)
        self.projectiles.draw(screen)
        self.explosions.draw(screen)
        self.house.draw(screen)
        self.pause_button.draw(screen)

        # ---------- отрисовка данных о танке ------------
        for tank in self.pl_tank:
            hp, pr_type = tank.get_info()
            font = pygame.font.Font(None, 50)
            text = font.render(str(hp), True, [255, 0, 0])
            screen.blit(text, (20, 20))
            if pr_type % 5 == 4:
                self.h_ex_proj.draw(screen)
            else:
                self.proj.draw(screen)
        # ---------отрисовка горения танков---------------
        for tank in self.en_tanks:
            tank.draw_fire()
        # ---------сколько врагов осталось----------------
        font = pygame.font.Font(None, 40)
        text = font.render(str(self.enemy_count + 3), True, [0, 0, 0])
        screen.blit(text, (20, 170))
        font = pygame.font.Font(None, 20)
        text = font.render('Врагов осталось:', True, [0, 0, 0])
        screen.blit(text, (10, 140))

    def update(self, *args):
        # ------------обработка кнопки паузы-----------------
        for btn in self.pause_button:
            btn.update(args)
            if btn.pressed():
                return
        # ------------обработка клавиш-направлений-------------------
        key = pygame.key.get_pressed()
        if key[pygame.K_UP]:
            for tank in self.pl_tank:
                tank.new_vy(-2)
        if key[pygame.K_DOWN]:
            for tank in self.pl_tank:
                tank.new_vy(2)
        elif key[pygame.K_LEFT]:
            for tank in self.pl_tank:
                tank.new_vx(-2)
        elif key[pygame.K_RIGHT]:
            for tank in self.pl_tank:
                tank.new_vx(2)
        # ------------обработка выстрела---------------------
        if key[pygame.K_SPACE] and self.pl_shoot:
            self.pl_shoot = False
            for tank in self.pl_tank:
                x, y, proj_type, dirctn = tank.get_pos()
            if proj_type == 0:
                HighExplosiveProjectile(x, y, dirctn, 'en', self.projectiles)
            else:
                Projectile(x, y, dirctn, 'en', self.projectiles)
        # ------------если игрок отпустил клавишу------------
        if args[0].type == pygame.KEYUP:
            if args[0].key == pygame.K_UP:
                for tank in self.pl_tank:
                    tank.new_vy(0)
            if args[0].key == pygame.K_DOWN:
                for tank in self.pl_tank:
                    tank.new_vy(0)
            if args[0].key == pygame.K_RIGHT:
                for tank in self.pl_tank:
                    tank.new_vx(0)
            if args[0].key == pygame.K_LEFT:
                for tank in self.pl_tank:
                    tank.new_vx(0)
            if args[0].key == pygame.K_SPACE:
                self.pl_shoot = True

    def update_(self):
        for btn in self.pause_button:
            if btn.pressed():
                return  # если пауза, ничего не делаем
        # ------------движение танка игрока------------------
        self.player_tank.move(self.en_tanks, self.walls)
        # ------------движение танка-------------------------   !!!!!!!
        for en_tank in self.en_tanks:
            en_tank.move(self.pl_tank, self.walls)
        # ------------движение снаряда-----------------------
        for projectile in self.projectiles:
            projectile.move(self.walls, self.explosions, self.house)
        # ------------обработка снарядов на поле-------------
        for tank in self.pl_tank:
            tank.proj_coll(self.projectiles, self.explosions)
        for tank in self.en_tanks:
            tank.proj_coll(self.projectiles, self.explosions)
        self.explosions.update()
        # ------------------ враг стреляет --------------------
        for tank in self.en_tanks:
            tank.shoot(self.projectiles)
        # ------------ обновление здоровья танков -------------
        self.en_tanks.update()
        self.pl_tank.update()
        for tank in self.en_tanks:
            result = tank.update_hp()
            if result:
                # ----- возрождение врагов -----
                self.enemy_count -= 1
                if self.enemy_count >= 0:
                    EnemyTank(choice(self.summon_coords), self.en_tanks)
        if self.enemy_count == -3:
            # ----- если все враги погибли, игрок побеждает -----
            game_stack.clear()
            game_stack.append(WinMenu())
        for tank in self.pl_tank:
            result = tank.update_hp()
            if result:
                # ----- если игрок погиб, он проиграл -----
                game_stack.clear()
                game_stack.append(LoseMenu())
        # ------------проверка на то, что игрок еще жив-----------
        if not bool(self.pl_tank):
            game_stack.clear()
            game_stack.append(LoseMenu())


# =======================================================================================


class WinMenu:
    '''Экран победы'''

    def update(self, *args):
        if args[0].type == pygame.MOUSEBUTTONDOWN:
            game_stack.clear()
            game_stack.append(StartMenu())

    def draw(self):
        screen.fill((200, 200, 200))
        font = pygame.font.Font(None, 180)
        text = font.render('WINNER!!!', True, [30, 240, 20])
        screen.blit(text, (80, 100))
        font = pygame.font.Font(None, 28)
        text = font.render('Нажми любую клавишу мышки, чтобы продолжить', True, [30, 240, 20])
        screen.blit(text, (150, 240))

    def update_(self):
        return


class LoseMenu:
    '''Экран поражения'''

    def update(self, *args):
        if args[0].type == pygame.MOUSEBUTTONDOWN:
            game_stack.clear()
            game_stack.append(StartMenu())

    def draw(self):
        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 180)
        text = font.render('LOSER!!!', True, [200, 0, 0])
        screen.blit(text, (120, 100))
        font = pygame.font.Font(None, 28)
        text = font.render('Нажми любую клавишу мышки, чтобы продолжить', True, [200, 0, 0])
        screen.blit(text, (150, 240))

    def update_(self):
        return


# ----------------------game-stack------------------------
game_stack = [StartMenu()]
# --------------------------------------------------------


running = True
while running:
    screen.fill((0, 0, 0))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break
        game_stack[-1].update(event)  # обработка событий
    game_stack[-1].update_()  # движение и прочие события. Позволяет двигать танк зажатием клавиши
    game_stack[-1].draw()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
