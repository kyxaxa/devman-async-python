from time import sleep
import asyncio
import curses
from random import choice, randint
from itertools import cycle
import logging
from sys import exit

from draw_blink import blink
from curses_tools import draw_frame, read_controls, get_frame_size
from read_data import read_all_text_frames

#   coding level. Will determine main debug settings.
level = 'production'
level = 'develop'

#   setup logging
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


def run_game(
        canvas,
        tic_timeout: float = 0.1,
        ) -> None:
    """
    Draw stars, ship and all other game objects.
    Run main loop to control all the object states.
    """
    cnt_stars = 200 # круто - 50_000 даже может :)
    star_symbols = [
        '*', '.', '+', ':',
    ]

    #   setup board
    curses.curs_set(False)
    canvas.nodelay(True)  # canvas.nodelay — сделать ввод неблокирующим
    canvas.border()

    height, width = canvas.getmaxyx()

    center_x = width // 2
    center_y = height // 2

    logging.debug(f'{height=} {width=}, {center_x=} {center_y=}')

    #   gathering all coroutines
    coroutines = []

    shot = animate_gun_shot(canvas, center_y, center_x, -0.5, 1)
    spaceship = animate_spaceship(canvas, center_y, center_x)

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

    # main event loop
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
        acceleration=3,
        want_limit_with_borders=1,
        ):
    """Control the spaceship"""
    frame1 = all_text_frames['rocket_frame_1.txt']
    frame2 = all_text_frames['rocket_frame_2.txt']

    frames = [
        frame1,
        frame2,
    ]
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

        if want_limit_with_borders:
            row = max(row, 0)
            row = min(row, max_row - max_frame_height)

            column = max(column, 0)
            column = min(column, max_column - max_frame_width)

        draw_frame(canvas, row, column, frame)

        [await asyncio.sleep(0) for _ in range(2)] #   кадры анимации сменяют друг друга раз в два кадра

        draw_frame(canvas, row, column, frame, negative=True)



if __name__ == '__main__':
    all_text_frames = read_all_text_frames()

    curses.update_lines_cols()

    curses.wrapper(run_game)
