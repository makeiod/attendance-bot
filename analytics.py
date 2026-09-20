import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import ConciseDateFormatter
import database

async def simple(user_id, timeframe, type):
    """Returns a simple line graph of a users attendance percentage throughout the year since joining the team"""
    percentages = await database.get_percentages(timeframe, user_id, type)
    plt.style.use('dark_background')
    fig, ax = plt.subplots()
    x, y = [], []
    i = 1
    for key in percentages:
        x.append(f'{i:02d}')
        y.append(percentages[key])
        i += 1
    plt.xlabel('Practice')
    plt.ylabel('Attendance Percent')
    plt.ylim(0, 105)
    ax.plot(x, y, marker='o', color='#002855', markerfacecolor='#B3A369')
    plt.savefig(f'{user_id}_report.png')
    plt.close()
    return f'{user_id}_report.png'
