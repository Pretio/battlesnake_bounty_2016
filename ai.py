import random


class Snake(object):
    def __init__(self, snake_id):
        self.snake_id = snake_id

    def start(self, payload):
        return {
            'taunt': 'cluck cluck cluck'
        }

    def move(self, payload):
        turn, snakes, food = payload['turn'], payload['snakes'], payload['food']
        width, height = payload['width'], payload['height']

        board = generate_board(payload)
        snake = self.get_snake(snakes)

        strategy = choose_strategy(
            turn=turn, board=board,
            snakes=snakes, snake=snake, food=food)

        result = strategy.get_action()

        if isinstance(result, tuple):
            direction, taunt = result
        else:
            direction, taunt = result, None

        # move, taunt
        return {
            'move': direction,
            'taunt': taunt,
        }

    def end(self, payload):
        return {
            'taunt': 'squaaaaaaawk!'
        }

    def get_snake(self, snakes):
        for snake in snakes:
            if snake.get('id') == self.snake_id:
                return snake

        raise KeyError('Failed to find snake')


#########################
# BOARD DATA
#########################

class Constants(object):
    UP = 'north'
    DOWN = 'south'
    LEFT = 'west'
    RIGHT = 'east'

    DIRECTIONS = (UP, DOWN, LEFT, RIGHT)

    HEAD = 'head'
    FOOD = 'food'
    BODY = 'body'
    EMPTY = 'empty'
    BOUNDARY = 'boundary'
    COLLISION = 'collision'


def generate_board(payload):
    width, height = payload['width'], payload['height']

    board = [
        [
            {'state': Constants.EMPTY}
            for y in range(height)
        ]
        for x in range(width)
    ]

    for coord in payload['food']:
        board[coord[0]][coord[1]]['state'] = Constants.FOOD

    for snake in payload['snakes']:
        for i, coord in enumerate(snake['coords']):
            if i == 0:
                board[coord[0]][coord[1]]['state'] = 'head'
            else:
                board[coord[0]][coord[1]]['state'] = 'body'
            board[coord[0]][coord[1]]['snake'] = snake['name']

    return board

def dimensions(board):
    ncols = len(board)
    nrows = len(board[0])
    return ncols, nrows

def adjacent(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

def manhattan_dist(pos1, pos2):
    return (abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]))

def square_loop_length(side_length):
    """
    Get the total length of a square loop with given `side_length`.

    eg. 2 --> 4
        3 --> 8
        4 --> 12
        ...
    """
    assert side_length >= 2
    return 2 * side_length + 2 * (side_length - 2)

def safe_square_size(snake_length):
    """
    Get the side length of a square loop that is safe for a snake
    of the specified length.

    eg. 1 --> 2
        2 --> 2
        3 --> 2
        4 --> 3
    """
    i = 2
    while square_loop_length(i) <= snake_length:
        i += 1
    return i

#########################
# AI
#########################

def choose_strategy(turn, board, snakes, snake, food):
    head = snake['coords'][0]
    health = snake['health']
    length = len(snake['coords'])

    if health > 40 and length < 4:
        # stay in the corner if we have food and haven't eaten
        strategy = FindCornerStrategy
    else:
        if health > 40:
            # don't collect food unless you absolutely have to
            strategy = AvoidFoodStrategy
        else:
            # prefer food when low on health
            strategy = FoodHuntingStrategy

    print 'STRATEGY:', strategy.__name__

    return strategy(turn, head, health, board, snakes, food)


class BaseStrategy(object):
    def __init__(self, turn, position, health, board, snakes, food):
        self.turn = turn
        self.position = position
        self.health = health
        self.board = board
        self.num_columns, self.num_rows = dimensions(self.board)
        self.snakes = [
            s for s in snakes if s['coords'][0] != self.position
        ]
        self.food = food

    def get_action(self):
        """ return (direction, taunt | None) """
        return Constants.UP, None

    def safe_directions(self, allowed_tiles=[Constants.EMPTY, Constants.FOOD]):
        good = []
        for d in Constants.DIRECTIONS:
            safe, contents = self.check_direction(d, allowed_tiles)
            if safe:
                good.append((d, contents))

        return good

    def check_direction(self, direction, allowed_tiles=[Constants.EMPTY, Constants.FOOD]):
        pos = self.position
        x = pos[0]
        y = pos[1]

        if direction == Constants.UP:
            y -= 1
        elif direction == Constants.DOWN:
            y += 1
        elif direction == Constants.LEFT:
            x -= 1
        else:
            x += 1

        return self.check_tile(x, y, allowed_tiles=allowed_tiles)

    def check_tile(self, x, y, allowed_tiles=[Constants.EMPTY, Constants.FOOD]):
        safe, contents = True, Constants.EMPTY

        # check the boundaries
        if (x >= self.num_columns or x < 0) or (y >= self.num_rows or y < 0):
            return False, Constants.BOUNDARY

        # check for invalid tile according to allowed_tiles
        tile = self.board[x][y]
        contents = tile['state']

        if contents not in allowed_tiles:
            safe = False

        # check for pending collision with other snakes
        for other_snake in self.snakes:
            other_snake_pos = other_snake['coords'][0]
            if adjacent(other_snake_pos, (x, y)):
                safe = False
                contents = Constants.COLLISION

        return safe, contents


class PreferFoodStrategy(BaseStrategy):
    def get_action(self):
        safe = self.safe_directions()

        if not safe:
            return Constants.UP, 'dying'

        for direction, contents in safe:
            if contents == Constants.FOOD:
                return direction

        direction, contents = random.choice(safe)

        return direction


class AvoidFoodStrategy(BaseStrategy):
    def get_action(self):
        safe = self.safe_directions()

        if not safe:
            return Constants.UP, 'dying'

        random.shuffle(safe)

        for direction, contents in safe:
            if contents != Constants.FOOD:
                return direction

        # only food??
        direction, contents = random.choice(safe)

        return direction


class FindCornerStrategy(BaseStrategy):
    """
    Move towards the nearest corner, if safe.

    This strategy is only safe to use if not within
    safe_square_size(snake.length) squares of the nearest corner.
    """
    def get_corners(self):
        return (
            (0, 0), (self.num_columns - 1, 0), (0, self.num_rows - 1), (self.num_columns - 1, self.num_rows - 1)
        )

    def get_closest_corners(self, board, position):
        corners = self.get_corners()

        safe_corners = filter(self.corner_is_safe, corners)

        return sorted(safe_corners, key=lambda corner:
            manhattan_dist(position, corner)
        )

    def corner_is_safe(self, corner):
        # a corner is only safe if it's completely empty and there are no
        # snakes able to move into it next turn
        safe, contents = self.check_tile(corner[0], corner[1], allowed_tiles=[Constants.EMPTY])
        return safe

    def get_action(self):
        empty = self.safe_directions(allowed_tiles=[Constants.EMPTY])
        corners = self.get_corners()

        x, y = self.position

        # try to move towards the closest empty corner
        for closest_corner in self.get_closest_corners(self.board, self.position):
            cx, cy = closest_corner

            print 'Looking for moves to safe corner:', (cx, cy)

            # FIXME: this doesn't quite work, because we aren't considering
            # the current corner as safe...

            if adjacent(self.position, closest_corner):
                # stay in corner, gross logic
                if closest_corner == corners[0]:
                    if x > cx and Constants.DOWN in empty:
                        return Constants.DOWN
                    if y > cy and Constants.RIGHT in empty:
                        return Constants.RIGHT
                if closest_corner == corners[1]:
                    if x < cx and Constants.DOWN in empty:
                        return Constants.DOWN
                    if y > cy and Constants.LEFT in empty:
                        return Constants.LEFT
                if closest_corner == corners[2]:
                    if x > cx and Constants.UP in empty:
                        return Constants.UP
                    if y < cy and Constants.RIGHT in empty:
                        return Constants.RIGHT
                if closest_corner == corners[3]:
                    if x < cx and Constants.UP in empty:
                        return Constants.UP
                    if y < cy and Constants.LEFT in empty:
                        return Constants.LEFT

            for direction, contents in empty:
                if direction == Constants.LEFT and cx < x:
                    return direction
                if direction == Constants.RIGHT and cx > x:
                    return direction
                if direction == Constants.UP and cy < y:
                    return direction
                if direction == Constants.DOWN and cy > y:
                    return direction

        # if we get here, we can't move toward any empty corner, just move randomly
        print "Can't move toward any corner!"
        direction, contents = random.choice(self.safe_directions())
        return direction


class StayInCornerStrategy(FindCornerStrategy):
    """
    Stay in the current corner.

    This strategy is only safe to use if within safe_square_size(snake.length)
    squares of the nearest corner.
    """
    def get_action(self):
        x, y = self.position

        corners = self.get_corners()
        empty = self.safe_directions(allowed_tiles=[Constants.EMPTY])

        for closest_corner in self.get_closest_corners(self.board, self.position):
            cx, cy = closest_corner

            if adjacent(self.position, closest_corner):
                # stay in corner, gross logic
                if closest_corner == corners[0]:
                    if x > cx and Constants.DOWN in empty:
                        return Constants.DOWN
                    if y > cy and Constants.RIGHT in empty:
                        return Constants.RIGHT
                if closest_corner == corners[1]:
                    if x < cx and Constants.DOWN in empty:
                        return Constants.DOWN
                    if y > cy and Constants.LEFT in empty:
                        return Constants.LEFT
                if closest_corner == corners[2]:
                    if x > cx and Constants.UP in empty:
                        return Constants.UP
                    if y < cy and Constants.RIGHT in empty:
                        return Constants.RIGHT
                if closest_corner == corners[3]:
                    if x < cx and Constants.UP in empty:
                        return Constants.UP
                    if y < cy and Constants.LEFT in empty:
                        return Constants.LEFT

        # if we get here, we can't stay in the corner, just move randomly
        direction, contents = random.choice(self.safe_directions())
        return direction


class FoodHuntingStrategy(BaseStrategy):
    """
    Move towards the nearest safe food, if there is a safe move in that direction.
    """
    def get_closest_food(self, board, position):
        safe_food = filter(self.food_is_safe, self.food)

        return sorted(safe_food, key=lambda food:
            manhattan_dist(position, food)
        )

    def food_is_safe(self, food):
        safe, contents = self.check_tile(food[0], food[1], allowed_tiles=[Constants.FOOD])
        return safe

    def get_action(self):
        safe = self.safe_directions(allowed_tiles=[Constants.EMPTY, Constants.FOOD])

        x, y = self.position

        # try to move towards the closest food
        for closest_food in self.get_closest_food(self.board, self.position):
            cx, cy = closest_food

            print 'Looking for moves to safe food:', (cx, cy)

            for direction, contents in safe:
                if direction == Constants.LEFT and cx < x:
                    return direction
                if direction == Constants.RIGHT and cx > x:
                    return direction
                if direction == Constants.UP and cy < y:
                    return direction
                if direction == Constants.DOWN and cy > y:
                    return direction

        # if we get here, we can't move toward anything useful, just move randomly
        print "Can't move toward any food!"
        direction, contents = random.choice(safe)
        return direction
