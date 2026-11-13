"""Orthogonal connectors around node boxes, with explicit draw.io waypoints."""
import heapq
import math

GAP = 24


def rectangle(g, margin=0):
    return (g["x"] - margin, g["y"] - margin,
            g["x"] + g["width"] + margin, g["y"] + g["height"] + margin)


def intersects(a, b, box):
    left, top, right, bottom = box
    if a[0] == b[0]:
        return left < a[0] < right and max(a[1], b[1]) > top and min(a[1], b[1]) < bottom
    return top < a[1] < bottom and max(a[0], b[0]) > left and min(a[0], b[0]) < right


def ports(g):
    x, y, w, h = (g[k] for k in ("x", "y", "width", "height"))
    return [((x + w, y + h / 2), (x + w + GAP, y + h / 2), (1, .5)),
            ((x + w / 2, y + h), (x + w / 2, y + h + GAP), (.5, 1)),
            ((x, y + h / 2), (x - GAP, y + h / 2), (0, .5)),
            ((x + w / 2, y), (x + w / 2, y - GAP), (.5, 0))]


def route(source, target, positions, previous=(), avoid=()):
    boxes = [rectangle(g, GAP - 1) for g in positions.values()]
    boxes += [(l - 4, t - 4, r + 4, b + 4) for l, t, r, b in avoid]
    starts, ends = ports(positions[source]), ports(positions[target])
    xs, ys = set(), set()
    for g in positions.values():
        for anchor, outside, _ in ports(g):
            xs.update((anchor[0], outside[0]))
            ys.update((anchor[1], outside[1]))
    for l, t, r, b in avoid:
        xs.update((l - 6, r + 6))
        ys.update((t - 6, b + 6))
    xs.update((min(xs) - GAP, max(xs) + GAP))
    ys.update((min(ys) - GAP, max(ys) + GAP))
    xs, ys = sorted(xs), sorted(ys)
    valid = {(x, y) for x in xs for y in ys
             if not any(l < x < r and t < y < b for l, t, r, b in boxes)}
    x_index, y_index = {x: i for i, x in enumerate(xs)}, {y: i for i, y in enumerate(ys)}
    distances, parents, heap = {}, {}, []
    def overlap_cost(a, b):
        penalty = 0
        for p, q in previous:
            if intersects(a, b, (min(p[0], q[0]) - 2, min(p[1], q[1]) - 2,
                                 max(p[0], q[0]) + 2, max(p[1], q[1]) + 2)):
                parallel = (a[0] == b[0]) == (p[0] == q[0])
                penalty += 500 if parallel else 80
        return penalty
    # Keep the source port in the search state; a self-loop must use another port.
    for index, (anchor, point, _) in enumerate(starts):
        if point in valid:
            axis = 0 if anchor[1] == point[1] else 1
            key = (point, axis, index)
            cost = GAP + overlap_cost(anchor, point)
            distances[key] = cost
            heapq.heappush(heap, (cost, key))
    destination = None
    best = math.inf
    while heap:
        cost, key = heapq.heappop(heap)
        point, axis, origin = key
        if cost != distances[key]:
            continue
        if cost >= best:
            break
        candidates = [i for i, (_, p, _) in enumerate(ends)
                      if p == point and (source != target or i != origin)]
        if candidates:
            for end_index in candidates:
                anchor, outside, _ = ends[end_index]
                final = cost + GAP + overlap_cost(outside, anchor)
                if final < best:
                    best, destination = final, (key, end_index)
        ix, iy = x_index[point[0]], y_index[point[1]]
        for nx, ny, new_axis in ((ix - 1, iy, 0), (ix + 1, iy, 0), (ix, iy - 1, 1), (ix, iy + 1, 1)):
            if not (0 <= nx < len(xs) and 0 <= ny < len(ys)):
                continue
            nxt = xs[nx], ys[ny]
            if nxt not in valid or any(intersects(point, nxt, box) for box in boxes):
                continue
            distance = abs(point[0] - nxt[0]) + abs(point[1] - nxt[1])
            candidate = cost + distance + (35 if new_axis != axis else 0) + overlap_cost(point, nxt)
            new_key = nxt, new_axis, origin
            if candidate < distances.get(new_key, math.inf):
                distances[new_key] = candidate
                parents[new_key] = key
                heapq.heappush(heap, (candidate, new_key))
    if destination is None:
        raise ValueError(f"Cannot route {source} → {target}; move overlapping/adjacent nodes apart")
    key, end_index = destination
    origin = key[2]
    chain = [ends[end_index][0]]
    while True:
        chain.append(key[0])
        if key not in parents:
            break
        key = parents[key]
    chain.append(starts[origin][0])
    chain.reverse()
    points = []
    for point in chain:
        while len(points) > 1 and ((points[-2][0] == points[-1][0] == point[0]) or
                                  (points[-2][1] == points[-1][1] == point[1])):
            points.pop()
        points.append(point)
    return points, starts[origin][2], ends[end_index][2]


def label_position(points, text, positions, used, segments=()):
    if not text:
        return None
    width, height = max(36, len(text) * 7.5 + 14), 22
    total = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:]))
    candidates, travelled = [], 0
    obstacles = [rectangle(g, 8) for g in positions.values()] + used
    obstacles += [(min(a[0], b[0]) - 3, min(a[1], b[1]) - 3,
                   max(a[0], b[0]) + 3, max(a[1], b[1]) + 3) for a, b in segments]
    for a, b in zip(points, points[1:]):
        length = abs(a[0] - b[0]) + abs(a[1] - b[1])
        for fraction in (.5, .25, .75):
            mid = (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)
            for dx, dy in ((0, -17), (0, 17)) if a[1] == b[1] else ((width / 2 + 8, 0), (-width / 2 - 8, 0)):
                cx, cy = mid[0] + dx, mid[1] + dy
                box = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
                if box[0] < 24 or box[1] < 140:
                    continue
                if any(box[0] < r and box[2] > l and box[1] < bottom and box[3] > top
                       for l, top, r, bottom in obstacles):
                    continue
                score = length - abs(fraction - .5) * 50
                candidates.append((score, 2 * (travelled + length * fraction) / total - 1, dx, dy, box))
        travelled += length
    if not candidates:
        raise ValueError(f"No clear space for edge label {text!r}; shorten it or adjust geometry")
    _, relative, dx, dy, box = max(candidates)
    used.append(box)
    return relative, dx, dy, box
