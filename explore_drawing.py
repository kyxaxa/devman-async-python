"""
никогда в curses не рисовал
тут разбираю разные приемы рисования
"""
from time import sleep
import curses
from draw_blink import blink


def draw_5_stars(canvas):
    cnt_stars = 5
    star_symbol = '*'

    curses.curs_set(False)

    row, column = (5, 20)
    canvas.border()

    stars = []

    for i in range(cnt_stars):
        column = column + 2
        star = blink(canvas, row, column, star_symbol)
        stars.append(star)

    tic_timeout = 0.1
    while True:
        for star in stars:
            star.send(None)
        canvas.refresh()
        sleep(tic_timeout)
        continue


def draw_star(canvas):
    curses.curs_set(False)

    row, column = (5, 20)
    canvas.border()

    star = '*'

    while True:
        canvas.addstr(row, column, star, curses.A_DIM)
        canvas.refresh()
        sleep(2)

        canvas.addstr(row, column, star)
        canvas.refresh()
        sleep(0.3)

        canvas.addstr(row, column, star, curses.A_BOLD)
        canvas.refresh()
        sleep(0.5)

        canvas.addstr(row, column, star)
        canvas.refresh()
        sleep(0.3)


if __name__ == '__main__':
    fun_draw = draw_5_stars
    fun_draw = draw_star

    curses.wrapper(fun_draw)
