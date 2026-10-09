"""Reference LTC3108 laboratory adapter: copper continuity regression.

Tests only validate the specified reference-board track connectivity. They do
not substitute for KiCad DRC, schematic ERC, isolation or measured startup.
All paths reproduce public LTC3108 example interface wiring, no new IP design.
"""
from collections import defaultdict, deque
from pathlib import Path
import re
import unittest

BOARD = Path(__file__).resolve().parents[1] / "hardware/active_power/ltc3108_power_breakout.kicad_pcb"
PATTERN = re.compile(
    r'\(segment \(start ([\d.]+) ([\d.]+)\) '
    r'\(end ([\d.]+) ([\d.]+)\) \(width ([\d.]+)\) '
    r'\(layer "([FB]\.Cu)"\) \(net (\d+)\)'
)


def copper_graph(source: str):
    graph = defaultdict(lambda: defaultdict(set))
    for ax, ay, bx, by, width, layer, net in PATTERN.findall(source):
        begin = (float(ax), float(ay))
        finish = (float(bx), float(by))
        key = (int(net), layer)
        graph[key][begin].add(finish)
        graph[key][finish].add(begin)
        if not 0.18 <= float(width) <= 0.60:
            raise ValueError(f"Unexpected trace width: {width}")
        if begin == finish:
            raise ValueError("Zero length segment")
    return graph


def connected(graph, key, start, end):
    queue = deque([start])
    visited = set()
    while queue:
        point = queue.popleft()
        if point == end:
            return True
        if point in visited:
            continue
        visited.add(point)
        queue.extend(graph[key].get(point, ()) - visited)
    return False


class ReferenceBoardRouting(unittest.TestCase):
    def test_known_charge_pump_reference_nets_unchanged(self):
        board = BOARD.read_text(encoding="utf-8")
        graph = copper_graph(board)
        self.assertTrue(connected(graph, (8,"F.Cu"), (59.1,17.0), (48.6,35.6825)))
        self.assertTrue(connected(graph, (9,"F.Cu"), (59.1,24.0), (48.6,35.0475)))

    def test_input_teg_and_return_wired_at_connectors(self):
        graph = copper_graph(BOARD.read_text(encoding="utf-8"))
        self.assertTrue(connected(graph, (11,"F.Cu"), (15.0,21.0), (25.0,21.0)))
        self.assertTrue(connected(graph, (1,"F.Cu"), (15.0,23.54), (25.0,23.54)))

    def test_external_primary_teg_and_ground_return(self):
        graph = copper_graph(BOARD.read_text(encoding="utf-8"))
        self.assertTrue(connected(graph, (11,"B.Cu"), (15.0,42.0), (25.0,21.0)))
        self.assertTrue(connected(graph, (1,"B.Cu"), (15.0,49.62), (25.0,23.54)))

    def test_3v3_output_and_storage_remain_separate(self):
        graph = copper_graph(BOARD.read_text(encoding="utf-8"))
        self.assertTrue(connected(graph, (4,"F.Cu"), (79.0,21.0), (68.0,35.0)))
        self.assertTrue(connected(graph, (3,"F.Cu"), (79.0,42.0), (68.0,45.0)))
        self.assertNotIn((68.0,45.0), graph[(4,"F.Cu")])
        self.assertNotIn((68.0,35.0), graph[(3,"F.Cu")])

    def test_decoupling_ground_is_not_crossed_by_storage_rail(self):
        graph = copper_graph(BOARD.read_text(encoding="utf-8"))
        self.assertTrue(connected(graph, (1,"B.Cu"), (68.0,37.54), (68.0,47.54)))
        self.assertNotIn((68.0,45.0), graph[(1,"B.Cu")])


if __name__ == "__main__":
    unittest.main()
