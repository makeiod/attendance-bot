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
    x, y = [], []
    for key in percentages:
        x.append(key)
        y.append(percentages[key])
    out = ax.plot(x, y, marker='o')
    plt.savefig(f'{user_id}_report.png')
    plt.close()
    return f'{user_id}_report.png'
