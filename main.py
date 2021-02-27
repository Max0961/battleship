import time as t
from random import randint


class Settings:
    size = 10

    ships = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

    appearance = {
        'none': '  ',
        'ship-space': '  ',
        'ship': '▓▓',
        'miss': '░░',
        'hit': '}{'
    }

    @property
    def ship_test(self):
        return [Ship(4, 1, 3, 5), Ship(2, 1, 0, 7), Ship(2, 0, 4, 0),
                Ship(1, 0, 6, 4), Ship(1, 0, 6, 6), Ship(1, 0, 1, 1),
                Ship(1, 0, 3, 3)]


class BoardException(Exception):
    def __init__(self, x, y):
        self.x = x
        self.y = y


class BoardUsedException(BoardException):
    def __str__(self):
        return 'В эту клетку уже стреляли'


class BoardOutException(BoardException):
    def __str__(self):
        return f'Клетка в позиции x = {self.x} и y = {self.y} вне доски'


class ShipGenerationFail(Exception):
    def __str__(self):
        return f'не удалось разместить корабли'


class Board:
    def __init__(self, size, is_enemy):
        self.size = size
        self.is_enemy = is_enemy
        self.ships = []
        self.board = [Cell(self, x, y)
                      for x in range(size)
                      for y in range(size)]

    @property
    def is_defeated(self):
        return all(map(lambda x: x.is_destroyed, self.ships))

    def get_cell(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.board[x * self.size + y]

    def has_space(self, ship):
        for d in range(ship.length):
            if ship.orientation:
                x, y = ship.x + d, ship.y
            else:
                x, y = ship.x, ship.y + d

            if not self.get_cell(x, y) or self.get_cell(x, y).is_space:
                return False

        return True

    def get_neighborhood(self, cell, orientation=None):
        if orientation is None:
            return (self.get_cell(cell.x + dx, cell.y + dy)
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1))

        elif orientation == 1:
            return (self.get_cell(cell.x, cell.y + dy)
                    for dy in (-1, 1))
        elif orientation == 0:
            return (self.get_cell(cell.x + dx, cell.y)
                    for dx in (-1, 1))
        else:
            return (self.get_cell(cell.x - 1, cell.y),
                    self.get_cell(cell.x + 1, cell.y),
                    self.get_cell(cell.x, cell.y - 1),
                    self.get_cell(cell.x, cell.y + 1))

    def build(self, ship):
        if not self.has_space(ship):
            return False

        cells = []

        for d in range(ship.length):
            if ship.orientation:
                cells.append(self.get_cell(ship.x + d, ship.y))
            else:
                cells.append(self.get_cell(ship.x, ship.y + d))

        for cell in cells:
            cell.ship = ship

        for cell in cells:
            for space_cell in self.get_neighborhood(cell):
                if space_cell and not space_cell.ship:
                    space_cell.is_space = True
                    ship.space_cells.append(space_cell)

        return True

    def get_not_shot_random_cell(self, special=None):
        if not special:
            cells = filter(lambda x: not x.shot_result_key, self.board)
        else:
            cells = filter(lambda x: not x.shot_result_key, special)

        cells = list(cells)

        if cells:
            return cells[randint(0, len(cells) - 1)]

    def get_free_random_cell(self):
        cells = filter(lambda x: not x.ship and not x.is_space, self.board)

        cells = list(cells)

        if cells:
            return cells[randint(0, len(cells) - 1)]

    def generate(self):
        for ship_type in Settings.ships:
            result = False
            counter = 0

            while not result:
                counter += 1
                random_cell = self.get_free_random_cell()

                if not random_cell or counter > self.size * self.size:
                    raise ShipGenerationFail()

                ship = Ship(
                    ship_type,
                    randint(0, 1),
                    random_cell.x,
                    random_cell.y
                )

                result = self.build(ship)

                if result:
                    self.ships.append(ship)

    def build_ships(self, ships):
        self.ships = ships
        for ship in ships:
            self.build(ship)

    def cell_out(self, x, y):
        if not 0 <= x < self.size or not 0 <= y < self.size:
            raise BoardOutException(x, y)

    def __str__(self):
        parts = ['    ', ' '.join(map(str, range(0, self.size))), '\n', '  ╔',
                 '═' * self.size * 2, '╗', '\n']

        for y in range(self.size):
            parts.append(f'{y} ║')

            for x in range(self.size):
                parts.append(f'{self.get_cell(x, y)}')

            parts.append('║\n')

        parts += ['  ╚', '═' * self.size * 2, '╝', '\n']
        return ''.join(parts)


class Ship:
    def __init__(self, length, orientation, x, y):
        self.length = length
        self.orientation = orientation
        self.x = x
        self.y = y
        self.lives = length
        self.space_cells = []
        self.names = ['Катер', 'Эсминец', 'Крейсер', 'Линкор']

    @property
    def is_destroyed(self):
        return not self.lives

    @property
    def name(self):
        return self.names[self.length - 1]

    def hit(self):
        self.lives -= 1

        if self.is_destroyed:
            for cell in self.space_cells:
                if not cell.shot_result_key:
                    cell.fire()


class Cell:
    def __init__(self, board, x, y):
        self.board = board
        self.x = x
        self.y = y
        self.is_space = False
        self.ship = None
        self.shot_results = {'miss': 'Мимо!', 'hit': 'Есть пробитие!',
                             'destroyed': 'Корабль уничтожен!'}
        self.shot_result_key = None

    @property
    def shot_result_text(self):
        if self.shot_result_key:
            text = self.shot_results[self.shot_result_key]
            if self.shot_result_key == 'destroyed':
                text = text.replace('Корабль', self.ship.name)
            return text

    def fire(self):
        if self.shot_result_key:
            raise BoardUsedException(self.x, self.y)

        if self.ship:
            self.ship.hit()
            self.shot_result_key = 'hit'

            if self.ship.is_destroyed:
                self.shot_result_key = 'destroyed'
        else:
            self.shot_result_key = 'miss'

    def __str__(self):
        if self.shot_result_key == 'hit' or self.shot_result_key == 'destroyed':
            return Settings.appearance['hit']

        if self.shot_result_key == 'miss':
            return Settings.appearance['miss']

        if self.ship and not self.shot_result_key and not self.board.is_enemy:
            return Settings.appearance['ship']

        if self.is_space and not self.board.is_enemy:
            return Settings.appearance['ship-space']

        return Settings.appearance['none']


class Player:
    def __init__(self, game, enemy):
        self.enemy = enemy
        self.game = game
        self.shot_cell = None

    def ask(self):
        print(self.shot_cell.shot_result_text)
        print(self.enemy)

        if self.won:
            print(self.win_text)
            self.game.ended = True

    def move(self):
        print(self.move_text)

        self.ask()
        while self.shot_cell.shot_result_key != 'miss' and not self.game.ended:
            self.ask()

    @property
    def win_text(self):
        raise NotImplementedError()

    @property
    def move_text(self):
        raise NotImplementedError()

    @property
    def won(self):
        return self.enemy.is_defeated


class AI(Player):
    hit_sequence = []

    def get_orientation(self):
        if len(self.hit_sequence) > 1:
            return self.hit_sequence[-1].x == self.hit_sequence[-2].x
        return 2

    def try_to_finish_off(self):
        candidates = [_ for _ in self.enemy.get_neighborhood(
            self.hit_sequence[-1], self.get_orientation()) if _]
        t.sleep(1)
        return self.enemy.get_not_shot_random_cell(candidates)

    def random_fire(self):
        t.sleep(1.5)
        return self.enemy.get_not_shot_random_cell()

    def ask(self):
        shot_cell = None

        # если есть попадание,
        # пытаемся найти оставшиеся клетки в окрестности
        if self.hit_sequence:
            shot_cell = self.try_to_finish_off()

            # если свободных клеток нет, то корабль уничтожен, или нужно
            # продолжить с другой стороны
            if not shot_cell:
                if self.hit_sequence[-1].shot_result_key == 'destroyed':
                    self.hit_sequence.clear()
                else:
                    self.hit_sequence.reverse()
                    shot_cell = self.try_to_finish_off()

        if not shot_cell:
            shot_cell = self.random_fire()

        print(f'Ход компьютера: {shot_cell.x} {shot_cell.y}')
        shot_cell.fire()

        if shot_cell.shot_result_key != 'miss':
            self.hit_sequence.append(shot_cell)

        self.shot_cell = shot_cell
        super().ask()

    @property
    def win_text(self):
        return 'Выиграл компютер!'

    @property
    def move_text(self):
        return 'Ходит компьютер!'


class User(Player):
    def ask(self):
        while True:
            input_string = input("Ваш ход: ").split()

            if len(input_string) != 2:
                print("Введите 2 координаты! ")
                continue

            x, y = input_string

            if not (x.isdigit()) or not (y.isdigit()):
                print("Введите числа! ")
                continue

            x, y = int(x), int(y)

            try:
                self.enemy.cell_out(x, y)
            except BoardOutException as e:
                print(e)
                continue

            shot_cell = self.enemy.get_cell(x, y)

            try:
                shot_cell.fire()
            except BoardUsedException as e:
                print(e)
                continue

            self.shot_cell = shot_cell
            super().ask()
            break

    @property
    def win_text(self):
        return 'Выиграл пользователь!'

    @property
    def move_text(self):
        return 'Ходит пользователь!'


class Game:
    def __init__(self):
        self.board_size = Settings.size

        self.user_board = Board(self.board_size, False)
        # self.user_board.build_ships(Settings().ship_test)
        self.user_board.generate()

        self.computer_board = Board(self.board_size, True)
        # self.computer_board.build_ships(Settings().ship_test)
        self.computer_board.generate()

        self.user = User(self, self.computer_board)
        self.computer = AI(self, self.user_board)

        self.ended = False

    @staticmethod
    def greet():
        print(" Дороу ")
        print(" формат ввода: x y ")
        print(" x - номер столбца ")
        print(" y - номер строки ")
        print()

    def loop(self):
        print("Доска пользователя:")
        print(self.user_board)
        print()

        counter = 0
        while not self.ended:
            if not counter % 2:
                self.user.move()
            else:
                self.computer.move()

            print()
            counter += 1

    def start(self):
        self.greet()
        self.loop()


g = Game()
g.start()
