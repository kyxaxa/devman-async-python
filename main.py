from time import sleep
import asyncio
import curses
from random import choice, randint
from itertools import cycle
from typing import List
import logging
import os

import configargparse

from draw_blink import blink
from curses_tools import draw_frame, read_controls, get_frame_size
from read_data_frames import read_all_text_frames, load_spaceship_frames

logger = logging.getLogger(__file__)


class SpaceGame:
    """Main class to setup and run the Space Game"""

    def __init__(
            self,
            tic_timeout: float = 0.1,
            cnt_stars: int = 200,
            unlimited_space: bool = False,
            spaceship_acceleration: int = 1,
            ) -> None:
        self.tic_timeout = tic_timeout
        self.cnt_stars = cnt_stars
        self.unlimited_space = unlimited_space
        self.spaceship_acceleration = spaceship_acceleration
        logger.debug(f'SpaceGame settings: {vars(self)}')

        self.all_text_frames = read_all_text_frames()

    def run(self):
        """Run the game"""
        curses.wrapper(
            draw_game,
            tic_timeout=self.tic_timeout,
            cnt_stars=self.cnt_stars,

            # spaceship settings
            unlimited_space=self.unlimited_space,
            spaceship_acceleration=self.spaceship_acceleration,
            spaceship_frames=load_spaceship_frames(self.all_text_frames),
        )


def draw_game(
        canvas,
        tic_timeout: float = 0.1,
        cnt_stars: int = 200,
        unlimited_space: bool = False,
        spaceship_acceleration: int = 3,
        spaceship_frames: list = None,
        ) -> None:
    """Draw all objects of the space game.

    ask: я уже описал все параметры в parse_game_arguments_from_console()
        * в help= , там как раз все специально для человека
        * в readme
        Получается я еще раз тут должен это все продублировать?
        Минус: в 3-х местах дублирую ненужное :(
        Как избегать дублирования документации?

    ask: я уже типы прописал в аргументах ф-ии. В док-строках их тоже нужно дублировать?

    Draw stars, ship and all other game objects.
    Run main loop to control all the object states.

    Args:
        tic_timeout: sleep time for main loop
        cnt_stars:  count stars on the sky
        unlimited_space: is space unlimited
        spaceship_acceleration: spaceship acceleration. Higher value == bigger step on mouse press
        spaceship_frames: list of text pictures of spaceship
    """

    if spaceship_frames is None:
        spaceship_frames = load_spaceship_frames()

    star_symbols = [
        '*', '.', '+', ':',
    ]

    #   setup game board
    curses.update_lines_cols()
    curses.curs_set(False)
    canvas.nodelay(True)  # canvas.nodelay — сделать ввод неблокирующим
    canvas.border()

    #   calculate used variables
    height, width = canvas.getmaxyx()

    center_x = width // 2
    center_y = height // 2

    logging.debug(f'{height=} {width=}, {center_x=} {center_y=}')

    #   gather all coroutines
    coroutines = []

    shot = animate_gun_shot(canvas, center_y, center_x, -0.5, 1)

    spaceship = animate_spaceship(canvas, center_y, center_x,
                                  unlimited_space=unlimited_space,
                                  acceleration=spaceship_acceleration,
                                  frames=spaceship_frames,
                                  )

    coroutines.extend([
        shot,
        spaceship,
    ])

    for _ in range(cnt_stars):
        row = randint(1, height - 1)
        column = randint(1, width - 1)
        star_symbol = choice(star_symbols)
        star = blink(canvas, row, column, star_symbol)
        coroutines.append(star)

    #   main event loop
    coroutines = set(coroutines)
    while coroutines:
        for coro in coroutines.copy():
            try:
                coro.send(None)
            except StopIteration:
                coroutines.discard(coro)

        canvas.refresh()
        sleep(tic_timeout)


async def animate_gun_shot(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified"""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        row_ = round(row)
        col_ = round(column)
        canvas.addstr(row_, col_, symbol)
        await asyncio.sleep(0)
        canvas.addstr(row_, col_, ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(
        canvas,
        start_row, start_column,
        frames: List[str],
        acceleration: int = 3,
        unlimited_space: bool = False,  # is space unlimited?
        ):
    """Control the spaceship"""
    frames_cycle = cycle(frames)

    heights, widths = zip(*[get_frame_size(frame) for frame in frames])
    max_frame_height = max(heights)
    max_frame_width = max(widths)

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    row, column = start_row, start_column

    for frame in frames_cycle:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        row = row + rows_direction * acceleration
        column = column + columns_direction * acceleration

        if not unlimited_space:
            row = max(row, 0)
            row = min(row, max_row - max_frame_height)

            column = max(column, 0)
            column = min(column, max_column - max_frame_width)

        draw_frame(canvas, row, column, frame)

        await asyncio.sleep(0)

        draw_frame(canvas, row, column, frame, negative=True)


def parse_game_args():
    """Parse all game arguments"""
    parser = configargparse.ArgParser(
        description='Space game: move your SpaceShip between the stars',
        # default_config_files=['*.env'],
    )

    parser.add(
        '-l', '--log_level',
        default='production', choices=['production', 'develop'],
        help="level of debugging details (production==write to file, develop=echo details to console)",
    )
    parser.add(
        '-t', '--tic_timeout',
        default=0.1, type=float,
        help="timeout after every tic in main loop",
    )
    parser.add(
        '--settings_file',
        default='settings.env',
        # required=True,
        is_config_file=True,
        help="config file path, lines in format `var=value`",
    )
    parser.add(
        '--log_file',
        help="file with game logs",
    )
    parser.add(
        '--cnt_stars',
        default=200, type=int,
        help="stars quantity",
    )
    parser.add(
        '--unlimited_space',
        default=False, type=bool, choices=[True, False],
        help="UnlimitedSpace mode. You'll be able to move the spaceship out of the sky. "
             "Otherwise your fly is limited with the game's borders.",
    )
    parser.add(
        '-a', '--spaceship_acceleration',
        default=3, type=int,
        help="spaceship acceleration. Higher value == bigger step on mouse press",
    )

    options = parser.parse_args()
    return options


def main():
    """
    ask: чем это лучше простой вставки после  if __name__ == '__main__':?
        Вызовы basicConfigи setLevel в отличие от getLogger меняют настройки программы и её поведение, а потому должны быть спрятаны внутри ifmain. Еще лучше — завести функцию def main и перенести настройки туда.
    """
    args = parse_game_args()

    logging.basicConfig(
        format='%(filename)s[:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
        level=logging.DEBUG,
    )

    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(lineno)04d | %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    game = SpaceGame(
        tic_timeout=args.tic_timeout,
        cnt_stars=args.cnt_stars,
        unlimited_space=args.unlimited_space,
        spaceship_acceleration=args.spaceship_acceleration,
    )
    game.run()


if __name__ == '__main__':
    main()

"""
* ask:
    Насколько его стоит заменить (count_stars, stars_count), если я этим сокращением пользуюсь 10 лет?

* ask: cycle_frames у меня это цикл фреймов 
    Cамо использование ф-ии cycle(frames) намекает что это и будет цикл фреймов
    cycled_frames было бы циклированные фреймы. Как по мне шило на мыло - или вы чувствуете что cycled_frames явно лучше? 
    Вообще заменил на frames_cycle (цикл фреймов)

"""