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


from settings import *
from draw_blink import blink
from curses_tools import draw_frame, read_controls, get_frame_size
from read_data import read_all_text_frames


def load_spaceship_frames(all_text_frames: dict = None) -> List[str]:
    """Loading default spaceship text frames"""
    if all_text_frames is None:
        all_text_frames = read_all_text_frames()
    frame1 = all_text_frames['rocket_frame_1.txt']
    frame2 = all_text_frames['rocket_frame_2.txt']

    spaceship_frames = [
        frame1,
        frame2,
    ]
    return spaceship_frames


def parse_arguments():
    """Parse all game arguments"""
    parser = argparse.ArgumentParser(description='Space game: move your SpaceShip between the stars')

    parser.add_argument('-l', '--log_level', default='production', choices=['production', 'develop'], help="level of debugging details (production==write to file, develop=echo details to console)")
    parser.add_argument('-t', '--tic_timeout', default=0.1, help="timeout after every tic in main loop")

    parser.add_argument('--cnt_stars', default=10, type=int, help="stars quantity")

    parser.add_argument('--limit_borders_for_spaceship_moves', default=True, action='store_true', help="limit borders for spaceship moves? If False you'll be able to move the spaceship out of the sky")
    parser.add_argument('-a', '--spaceship_acceleration', default=3, type=int, help="spaceship acceleration. Higher value == bigger step on mouse press")

    args = parser.parse_args()
    return args


def setup_logging(level="production"):
    """setup logging depending on level"""

    if level == 'develop':
        logging.basicConfig(format='%(filename)s[:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                            level=logging.DEBUG,
                            )
    elif level == 'production':
        logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(message)s',
                            level=logging.DEBUG,
                            filename='temp/game_log.log',
                            )
    else:
        logging.critical(f'UNKNOWN {level=}')
        exit(0)


class SpaceGame:
    """Main class to setup and run the Space Game"""

    def __init__(self):
        args = parse_arguments()
        self.args = args

        setup_logging(args.log_level)

        self.all_text_frames  = read_all_text_frames()


    def run(self):
        curses.wrapper(
            run_game,
            tic_timeout=self.args.tic_timeout,
            cnt_stars=self.args.cnt_stars,

            # spaceship settings
            limit_borders_for_spaceship_moves=self.args.limit_borders_for_spaceship_moves,
            spaceship_acceleration=self.args.spaceship_acceleration,
            spaceship_frames=load_spaceship_frames(self.all_text_frames),
        )


def run_game(
        canvas,
        tic_timeout: float = 0.1,
        cnt_stars: int = 200,  # круто - 50_000 даже может :)
        limit_borders_for_spaceship_moves : bool = True,
        spaceship_acceleration : int = 3,
        spaceship_frames : list = None,
        ) -> None:
    """
    Draw stars, ship and all other game objects.
    Run main loop to control all the object states.
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
                                  limit_with_borders=limit_borders_for_spaceship_moves,
                                  acceleration=spaceship_acceleration,
                                  frames = spaceship_frames,
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
    """Display animation of gun shot, direction and speed can be specified."""

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
        frames: List[str] = [],
        acceleration: int = 3,
        limit_with_borders: bool = True,
        ):
    """Control the spaceship"""
    cycle_frames = cycle(frames)

    frames_sizes = [get_frame_size(frame) for frame in frames]
    max_frame_height = max(_[0] for _ in frames_sizes)
    max_frame_width = max(_[1] for _ in frames_sizes)

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    row, column = start_row, start_column

    for frame in cycle_frames:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        row = row + rows_direction * acceleration
        column = column + columns_direction * acceleration

        if limit_with_borders:
            row = max(row, 0)
            row = min(row, max_row - max_frame_height)

            column = max(column, 0)
            column = min(column, max_column - max_frame_width)

        draw_frame(canvas, row, column, frame)

        [await asyncio.sleep(0) for _ in range(2)]  # кадры анимации сменяют друг друга раз в два кадра

        draw_frame(canvas, row, column, frame, negative=True)


if __name__ == '__main__':
    game = SpaceGame()
    game.run()
