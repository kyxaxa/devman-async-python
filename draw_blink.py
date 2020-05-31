from random import randint
import asyncio
import curses


async def blink(canvas, row, column, symbol='*'):
    while True:
        random_delay = randint(0, 40)
        await await_for(random_delay)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        await await_for(20)

        canvas.addstr(row, column, symbol)
        await await_for(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await await_for(5)

        canvas.addstr(row, column, symbol)
        await await_for(3)


async def await_for(cnt=5):
    for i in range(cnt):
        await asyncio.sleep(0)


if __name__ == "__main__":
    pass
