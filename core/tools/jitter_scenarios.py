#!/usr/bin/env python3
"""Generate N flat scenario JSONs with random positions within field bounds.

Field: 9x6 (x ∈ [-4.5, 4.5], y ∈ [-3.0, 3.0])
Min spacing between any two entities: 0.5m
Ball not inside any bot.
Deterministic seed for reproducibility.
"""

import json
import os
import random

FIELD_X_MIN, FIELD_X_MAX = -4.5, 4.5
FIELD_Y_MIN, FIELD_Y_MAX = -3.0, 3.0
MIN_SPACING = 0.5
N = 12
SEED = 20260825
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'scenario')

BOT_LABELS = ['blue_1', 'blue_2', 'blue_3', 'red_1', 'red_2', 'red_3']

SITUATIONS = [
    "midfield ball — both teams in transition",
    "ball near left wing — red pressing",
    "ball in blue half — blue defending deep",
    "ball in red half — blue attacking with numbers",
    "ball near right wing — blue possession",
    "ball at center — even midfield battle",
    "ball in blue half — red counter-attack",
    "ball in red half — blue pressing high",
    "ball near left corner — blue has space on right",
    "ball near center circle — both teams recovering",
    "ball in blue half — blue holding for counter",
    "ball near right flank — red defense shifting",
]


def random_position(exclude_positions):
    for _ in range(100):
        x = round(random.uniform(FIELD_X_MIN, FIELD_X_MAX), 3)
        y = round(random.uniform(FIELD_Y_MIN, FIELD_Y_MAX), 3)
        ok = True
        for ex, ey in exclude_positions:
            if ((x - ex) ** 2 + (y - ey) ** 2) ** 0.5 < MIN_SPACING:
                ok = False
                break
        if ok:
            return x, y
    return None


def generate():
    random.seed(SEED)
    os.makedirs(SCENARIO_DIR, exist_ok=True)

    for i in range(N):
        entities = {}
        excludes = []

        # Ball first
        bx, by = random_position([])
        entities['soccer_ball'] = {'x': bx, 'y': by}
        excludes.append((bx, by))

        # Bots
        for label in BOT_LABELS:
            pos = random_position(excludes)
            if pos is None:
                bx, by = random_position([])
                entities[label] = {'x': bx, 'y': by}
                excludes.append((bx, by))
            else:
                entities[label] = {'x': pos[0], 'y': pos[1]}
                excludes.append(pos)

        scenario = {
            'scenario_name': f'jit_{i+1:03d}',
            'mode': '3vs3',
            'tactical_situation': SITUATIONS[i % len(SITUATIONS)],
            'entities': entities,
        }

        path = os.path.join(SCENARIO_DIR, f'jit_{i+1:03d}.json')
        with open(path, 'w') as f:
            json.dump(scenario, f, indent=4)
        print(f'  {path}')


if __name__ == '__main__':
    generate()