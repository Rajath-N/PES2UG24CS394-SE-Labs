import random
import pygame

WIDTH, HEIGHT = 800, 600
GRAVITY, JUMP_SPEED, WALK_SPEED = 1500, -640, 220
BUBBLE_TRAVEL, BUBBLE_LIFE = 0.45, 8.0

PLATFORMS = [
    pygame.Rect(0, 570, WIDTH, 30),
    pygame.Rect(0, 450, 300, 16),
    pygame.Rect(500, 450, 300, 16),
    pygame.Rect(150, 330, 500, 16),
    pygame.Rect(0, 210, 250, 16),
    pygame.Rect(550, 210, 250, 16),
]

SPAWNS = [
    (200, 330),
    (600, 330),
    (100, 210),
    (700, 210),
    (150, 450),
    (650, 450),
    (400, 330),
    (60, 570),
]


def bubble_tint(bubble):
    """Return a colour based on the bubble's remaining life."""
    if bubble.enemy is not None:
        return (255, 120, 200)

    life_ratio = max(0.0, min(1.0, bubble.life / BUBBLE_LIFE))
    red = int(100 + 155 * (1 - life_ratio))
    green = int(220 - 80 * (1 - life_ratio))
    blue = int(255 - 40 * (1 - life_ratio))
    return (red, green, blue)


def on_fruit_collected(fruit):
    """Handle fruit collection while preserving its point value."""
    return fruit.value


def bonus_life_threshold():
    """Award an extra life for every 5000 points."""
    return 5000


class Body:
    """Anything that falls and lands on platforms."""

    def __init__(self, x, y, w, h):
        self.x = float(x)
        self.y = float(y)
        self.w = w
        self.h = h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x - self.w / 2),
            round(self.y - self.h),
            self.w,
            self.h
        )

    @property
    def center(self):
        return pygame.Vector2(
            self.x,
            self.y - self.h / 2
        )

    def move(self, dt):
        self.vy = min(
            self.vy + GRAVITY * dt,
            900
        )

        previous_bottom = self.y

        self.x += self.vx * dt

        self.x = max(
            self.w / 2,
            min(
                WIDTH - self.w / 2,
                self.x
            )
        )

        self.y += self.vy * dt
        self.on_ground = False

        if self.vy >= 0:
            for plat in PLATFORMS:

                overlaps = (
                    self.x + self.w / 2 > plat.left
                    and
                    self.x - self.w / 2 < plat.right
                )

                crossed_platform = (
                    previous_bottom <= plat.top
                    and self.y >= plat.top
                )

                if overlaps and crossed_platform:
                    self.y = plat.top
                    self.vy = 0.0
                    self.on_ground = True
                    break


class Player(Body):

    def __init__(self):
        super().__init__(
            WIDTH / 2,
            570,
            30,
            30
        )

        self.facing = 1
        self.cooldown = 0.0
        self.invulnerable = 2.0

    def update(self, dt, keys):

        direction = (
            int(keys[pygame.K_RIGHT])
            - int(keys[pygame.K_LEFT])
        )

        if direction != 0:
            self.facing = direction

        self.vx = direction * WALK_SPEED

        self.cooldown = max(
            0.0,
            self.cooldown - dt
        )

        self.invulnerable = max(
            0.0,
            self.invulnerable - dt
        )

        self.move(dt)


class Enemy(Body):

    def __init__(self, x, y, angry=False):
        super().__init__(
            x,
            y,
            28,
            28
        )

        self.speed = 130 if angry else 70
        self.direction = random.choice([-1, 1])
        self.think = 0.0

    def update(self, dt, player):

        self.think -= dt

        if self.think <= 0:

            if abs(player.x - self.x) > 8:
                self.direction = (
                    1 if player.x > self.x else -1
                )

            self.think = random.uniform(
                0.4,
                1.2
            )

        self.vx = self.direction * self.speed

        if (
            self.on_ground
            and player.y < self.y - 40
            and random.random() < dt * 1.5
        ):
            self.vy = JUMP_SPEED

        self.move(dt)


class Bubble:

    def __init__(self, x, y, direction):

        self.pos = pygame.Vector2(
            x,
            y
        )

        self.vel = pygame.Vector2(
            direction * 260,
            0
        )

        self.age = 0.0
        self.enemy = None
        self.life = BUBBLE_LIFE

    @property
    def radius(self):
        return 22 if self.enemy else 14

    def update(self, dt):

        self.age += dt

        if self.age >= BUBBLE_TRAVEL:

            self.vel.x *= max(
                0.0,
                1.0 - 3.0 * dt
            )

            self.vel.y = -70

        self.pos += self.vel * dt

        self.pos.x = max(
            self.radius,
            min(
                WIDTH - self.radius,
                self.pos.x
            )
        )

        if self.enemy is not None:
            self.life -= dt


class Fruit(Body):

    def __init__(self, x, y, value):

        super().__init__(
            x,
            y,
            18,
            18
        )

        self.value = value
        self.life = 10.0

    def update(self, dt):

        self.life -= dt
        self.move(dt)


class Game:

    def __init__(self):

        self.font = pygame.font.Font(
            None,
            26
        )

        self.big_font = pygame.font.Font(
            None,
            42
        )

        self.reset()

    def reset(self):

        self.level = 1
        self.score = 0
        self.lives = 3
        self.combo = 0
        self.state = "play"

        self.bonus_awarded = 0

        self.player = Player()
        self.fruits = []

        self.start_level()

    def start_level(self):

        self.bubbles = []

        count = min(
            8,
            2 + self.level
        )

        count = min(
            count,
            len(SPAWNS)
        )

        self.enemies = [
            Enemy(x, y)
            for x, y in random.sample(
                SPAWNS,
                count
            )
        ]

    def blow_bubble(self):

        if self.state != "play":
            return

        player = self.player

        if player.cooldown > 0:
            return

        player.cooldown = 0.3

        bubble = Bubble(
            player.x + player.facing * 24,
            player.center.y,
            player.facing
        )

        self.bubbles.append(bubble)

    def trap_enemies(self, bubble):
        if bubble.enemy is not None:
            return

        if bubble.age >= 1.5:
            return

        for enemy in self.enemies[:]:
            distance_squared = bubble.pos.distance_squared_to(enemy.center)
            threshold = bubble.radius + 14

            if distance_squared <= threshold * threshold:
                self.enemies.remove(enemy)
                enemy.vx = 0
                enemy.vy = 0
                bubble.enemy = enemy
                bubble.vel.x = 0
                bubble.vel.y = -70
                return

    def pop(self, bubble):

        if bubble not in self.bubbles:
            return

        self.bubbles.remove(bubble)

        if bubble.enemy is not None:

            self.combo += 1

            points = 100 * self.combo

            self.score += points

            fruit = Fruit(
                bubble.pos.x,
                bubble.pos.y,
                points
            )

            self.fruits.append(fruit)

        self.player.vy = -260

    def release(self, bubble):

        if bubble not in self.bubbles:
            return

        self.bubbles.remove(bubble)

        if bubble.enemy is None:
            return

        enemy = bubble.enemy

        enemy.x = bubble.pos.x
        enemy.y = bubble.pos.y + enemy.h / 2

        enemy.speed = 130
        enemy.vx = 0
        enemy.vy = 0

        self.enemies.append(enemy)

    def player_hits_enemy(self):

        if self.player.invulnerable > 0:
            return False

        for enemy in self.enemies:

            if self.player.rect.colliderect(
                enemy.rect
            ):
                return True

        return False

    def update(self, dt, keys):

        if self.state != "play":
            return

        player = self.player

        player.update(
            dt,
            keys
        )

        if player.on_ground:
            self.combo = 0

        if keys[pygame.K_SPACE]:
            self.blow_bubble()

        threshold = bonus_life_threshold()

        if threshold is not None:

            earned_bonus = (
                self.score // threshold
            )

            if earned_bonus > self.bonus_awarded:

                new_lives = (
                    earned_bonus
                    - self.bonus_awarded
                )

                self.lives += new_lives

                self.bonus_awarded = earned_bonus

        for enemy in self.enemies[:]:
            enemy.update(
                dt,
                player
            )

        for bubble in self.bubbles[:]:

            bubble.update(dt)

            self.trap_enemies(
                bubble
            )

            if bubble.enemy is not None:

                player_can_pop = (
                    player.vy > 0
                    and
                    player.center.distance_to(
                        bubble.pos
                    )
                    <= bubble.radius + 18
                )

                if player_can_pop:
                    self.pop(bubble)

                elif bubble.life <= 0:
                    self.release(bubble)

            else:

                if bubble.pos.y < -bubble.radius:
                    if bubble in self.bubbles:
                        self.bubbles.remove(
                            bubble
                        )

        for fruit in self.fruits[:]:

            fruit.update(dt)

            if fruit.rect.colliderect(
                player.rect
            ):

                value = on_fruit_collected(
                    fruit
                )

                self.score += value

                self.fruits.remove(
                    fruit
                )

            elif fruit.life <= 0:

                self.fruits.remove(
                    fruit
                )

        if self.player_hits_enemy():

            self.lives -= 1

            if self.lives <= 0:

                self.state = "lose"

            else:

                self.player = Player()

        if (
            len(self.enemies) == 0
            and
            not any(
                bubble.enemy is not None
                for bubble in self.bubbles
            )
        ):

            self.level += 1

            self.start_level()

    def draw(self, screen):

        screen.fill(
            (14, 16, 40)
        )

        for plat in PLATFORMS:

            pygame.draw.rect(
                screen,
                (90, 60, 160),
                plat
            )

            pygame.draw.rect(
                screen,
                (150, 120, 220),
                (
                    plat.left,
                    plat.top,
                    plat.width,
                    4
                )
            )

        for fruit in self.fruits:

            pygame.draw.circle(
                screen,
                (230, 60, 80),
                (
                    int(fruit.center.x),
                    int(fruit.center.y)
                ),
                9
            )

            pygame.draw.circle(
                screen,
                (255, 180, 80),
                (
                    int(fruit.center.x),
                    int(fruit.center.y)
                ),
                12,
                2
            )

        for enemy in self.enemies:

            color = (
                (240, 90, 60)
                if enemy.speed > 100
                else (240, 160, 50)
            )

            pygame.draw.rect(
                screen,
                color,
                enemy.rect,
                border_radius=6
            )

            pygame.draw.circle(
                screen,
                (255, 255, 255),
                enemy.center - (5, 3),
                3
            )

            pygame.draw.circle(
                screen,
                (255, 255, 255),
                enemy.center + (5, -3),
                3
            )

        for bubble in self.bubbles:

            color = bubble_tint(
                bubble
            )

            pygame.draw.circle(
                screen,
                color,
                (
                    int(bubble.pos.x),
                    int(bubble.pos.y)
                ),
                bubble.radius,
                3
            )

            if bubble.enemy is not None:

                pygame.draw.circle(
                    screen,
                    (240, 160, 50),
                    (
                        int(bubble.pos.x),
                        int(bubble.pos.y)
                    ),
                    9
                )

        player = self.player

        if (
            player.invulnerable <= 0
            or
            int(
                player.invulnerable * 10
            ) % 2 == 0
        ):

            pygame.draw.rect(
                screen,
                (70, 210, 110),
                player.rect,
                border_radius=8
            )

            eye = (
                player.center
                +
                pygame.Vector2(
                    player.facing * 6,
                    -4
                )
            )

            pygame.draw.circle(
                screen,
                (255, 255, 255),
                (
                    int(eye.x),
                    int(eye.y)
                ),
                4
            )

        hud = self.font.render(
            f"Score: {self.score}    "
            f"Lives: {self.lives}    "
            f"Level: {self.level}    "
            f"Combo: {self.combo}",
            True,
            (240, 240, 240)
        )

        screen.blit(
            hud,
            (10, 8)
        )

        controls = self.font.render(
            "Arrow Keys: Move   "
            "UP: Jump   "
            "SPACE: Bubble   "
            "R: Reset",
            True,
            (190, 190, 210)
        )

        screen.blit(
            controls,
            (10, 36)
        )

        if self.state == "lose":

            overlay = pygame.Surface(
                (WIDTH, HEIGHT),
                pygame.SRCALPHA
            )

            overlay.fill(
                (0, 0, 0, 150)
            )

            screen.blit(
                overlay,
                (0, 0)
            )

            label = self.big_font.render(
                "GAME OVER",
                True,
                (255, 255, 120)
            )

            restart = self.font.render(
                "Press R to restart",
                True,
                (255, 255, 255)
            )

            screen.blit(
                label,
                label.get_rect(
                    center=(
                        WIDTH // 2,
                        HEIGHT // 2 - 25
                    )
                )
            )

            screen.blit(
                restart,
                restart.get_rect(
                    center=(
                        WIDTH // 2,
                        HEIGHT // 2 + 25
                    )
                )
            )


def main():

    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )

    pygame.display.set_caption(
        "Bubble Bobble"
    )

    clock = pygame.time.Clock()

    game = Game()

    running = True

    while running:

        dt = min(
            clock.tick(60) / 1000.0,
            0.05
        )

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_UP
            ):

                if game.player.on_ground:
                    game.player.vy = JUMP_SPEED

            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_r
            ):

                game.reset()

        keys = pygame.key.get_pressed()

        game.update(
            dt,
            keys
        )

        game.draw(
            screen
        )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()