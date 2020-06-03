from time import sleep
import asyncio
import curses
from random import choice, randint
from itertools import cycle
import logging
from sys import exit
import argparse
from typing import List
import os

from settings import load_settings_from_file_to_environment
from draw_blink import blink
from curses_tools import draw_frame, read_controls, get_frame_size
from read_data_frames import read_all_text_frames, load_spaceship_frames
import errors

logger = logging.getLogger('space_game')


def parse_game_arguments_from_console():
    """Parse all game arguments from console"""

    class MarkNonedefault(argparse.Action):
        """Mark if the variable is not default (user-defined, from console)"""
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            setattr(namespace, f'{self.dest}_nondefault', True)

    parser = argparse.ArgumentParser(description='Space game: move your SpaceShip between the stars')

    parser.add_argument('-l', '--log_level',
                        default='production', choices=['production', 'develop'],
                        help="level of debugging details (production==write to file, develop=echo details to console)",
                        action=MarkNonedefault,
                        )
    parser.add_argument('-t', '--tic_timeout',
                        default=0.1, help="timeout after every tic in main loop",
                        action=MarkNonedefault,
                        )
    parser.add_argument('--settings_file',
                        default='settings.env',
                        help="file with settings, lines in format `var=value`",
                        action=MarkNonedefault,
                        )
    parser.add_argument('--log_file',
                        default='temp/game_logs.log', help="file with game logs",
                        action=MarkNonedefault,
                        )

    parser.add_argument('--cnt_stars',
                        default=200, type=int, help="stars quantity",
                        action=MarkNonedefault,
                        )

    parser.add_argument('--unlimited_space',
                        # action='store_true',
                        default=False,
                        type=bool,
                        choices=[True, False],
                        help="UnlimitedSpace mode. You'll be able to move the spaceship out of the sky. "
                        "Otherwise your fly is limited with the game's borders.",
                        action=MarkNonedefault,
                        )
    parser.add_argument('-a', '--spaceship_acceleration',
                        default=3, type=int,
                        help="spaceship acceleration. Higher value == bigger step on mouse press",
                        action=MarkNonedefault,
                        )

    args = parser.parse_args()
    return args


class UserVars:
    """Reading user variables from console or from the environment.

    Vars to environment were sent through the file with that vars."""

    def __init__(self):
        self.args = parse_game_arguments_from_console()

        if self.get_nonDefault_variable_from_commandLine('settings_file') is not None \
                and not os.path.isfile(self.args.settings_file):  # user defined file with settings should exists
            raise errors.NoFileError(self.args.settings_file)

        if os.path.isfile(self.args.settings_file):
            load_settings_from_file_to_environment(self.args.settings_file)

        self.vars = self.get_user_variables()

    def get_user_variables(self):
        descriptions = [
            ('tic_timeout', float),
            ('cnt_stars', int),
            ('unlimited_space', bool),
            ('spaceship_acceleration', int),
            ('log_file', str),
            ('settings_file', str),
        ]
        vars = {}
        for name, to_type in descriptions:
            value = self.get_user_variable(name, to_type)
            vars[name] = value

        return vars

    def get_user_variable(self, name: str = 'tic_timeout', to_type: callable = None):
        """Search for user variable.

        Search order:
            * in command line
            * in system variables
            * in defaults

        to_type: if is not None, convert it to that type
        """

        possible_values = [
            ('command line', self.get_nonDefault_variable_from_commandLine(name, None)),
            ('environment', os.getenv(name, None)),
            ('command line default', getattr(self.args, name)),
        ]

        for found, var in possible_values:
            if var is not None:
                break

        if to_type == bool and isinstance(var, str) and var.lower() in ['false', '0']:  # dotenv don't understand bool
            var = False

        if to_type is not None:
            var = to_type(var)

        logger.debug(f'    {name} = {var}, in {found=}, {type(var)=}')

        return var

    def get_nonDefault_variable_from_commandLine(self, name: str = 'tic_timeout', default=None):
        """Get non-default variable from command line"""
        name_nondefault = f'{name}_nondefault'
        var = getattr(self.args, name) if hasattr(self.args, name_nondefault) else default
        return var


class SpaceGame(UserVars):
    """Main class to setup and run the Space Game"""

    def __init__(self):
        super().__init__()

        self.setup_logging(self.args.log_level)

        self.all_text_frames = read_all_text_frames()

    def setup_logging(self, level="production") -> None:
        """Setup logging depending on level.
        
        Args:
            level (str): production or develop
        """
        logger.setLevel(logging.DEBUG)

        if level == 'develop':
            logging.basicConfig(format='%(filename)s[:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                                )
        elif level == 'production':
            logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(message)s',
                                level=logging.DEBUG,
                                filename=self.vars['log_file'],
                                )
        else:
            logger.critical(f'UNKNOWN {level=}')

    def run(self):
        """Run the game"""
        curses.wrapper(
            draw_game,
            tic_timeout=self.vars['tic_timeout'],
            cnt_stars=self.vars['cnt_stars'],

            # spaceship settings
            unlimited_space=self.vars['unlimited_space'],
            spaceship_acceleration=self.vars['spaceship_acceleration'],
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


if __name__ == '__main__':
    game = SpaceGame()
    game.run()

"""
* ask: насколько стоил усложнять ввод кучей вариантов - и консолью, и глобальными переменными? 
    И потом их комплексной обработкой? Тут обработка этих переменных занимает больше кода чем сама игра.
    Или это для обучения?
    
* ask: cnt_stars - я всегда использую cnt_ как сокращение от count_ . 
    Насколько его стоит заменить (count_stars, stars_count), если я этим сокращением пользуюсь 10 лет?

* ask: cycle_frames у меня это цикл фреймов 
    Cамо использование ф-ии cycle(frames) намекает что это и будет цикл фреймов
    cycled_frames было бы циклированные фреймы. Как по мне шило на мыло - или вы чувствуете что cycled_frames явно лучше? 
    Вообще заменил на frames_cycle (цикл фреймов)

"""