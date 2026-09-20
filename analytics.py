import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import ConciseDateFormatter
import database

async def simple(user_id, timeframe, type):
    """Returns a simple line graph of a users attendance percentage throughout the year since joining the team"""
    percentages = await database.get_percentages(timeframe, user_id, type)
    fig, ax = plt.subplots()
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')   
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.grid(color='gray', linestyle='--', alpha=0.3)
    x, y = [], []
    i = 1
    for key in percentages:
        x.append(f'{i:02d}')
        y.append(percentages[key])
        i += 1
    plt.xlabel('Practice')
    plt.ylabel('Attendance Percent')
    plt.ylim(0, 105)
    ax.plot(x, y, marker='o', markerfacecolor='white', color='#B3A369', linewidth=3)
    plt.savefig(f'{user_id}_report.png', transparent=True)
    plt.close()
    return f'{user_id}_report.png'
