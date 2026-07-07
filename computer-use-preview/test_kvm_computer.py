import unittest

from computers.kvm.kvm import KvmComputer


class TestKvmComputer(unittest.TestCase):

    def test_click_uses_abs_route_with_full_screen_geometry(self):
        computer = KvmComputer(node_url="http://node", screen_size=(1920, 1080))
        calls = []

        def fake_run(route, payload, scheme="kvm", timeout=60):
            calls.append((route, payload, scheme, timeout))
            if route == "screen/query/capture":
                return {"pngBase64": ""}
            return {"ok": True}

        computer._run = fake_run

        computer.click_at(1254, 400)

        self.assertEqual(calls[0][0], "abs/command/click")
        self.assertEqual(
            calls[0][1],
            {"x": 1254, "y": 400, "sw": 1920, "sh": 1080, "button": "left", "do_click": True},
        )

    def test_hover_uses_abs_route_without_click(self):
        computer = KvmComputer(node_url="http://node", screen_size=(1920, 1080))
        calls = []

        def fake_run(route, payload, scheme="kvm", timeout=60):
            calls.append((route, payload, scheme, timeout))
            if route == "screen/query/capture":
                return {"pngBase64": ""}
            return {"ok": True}

        computer._run = fake_run

        computer.hover_at(700, 300)

        self.assertEqual(calls[0][0], "abs/command/click")
        self.assertEqual(calls[0][1]["do_click"], False)
        self.assertEqual(calls[0][1]["sw"], 1920)
        self.assertEqual(calls[0][1]["sh"], 1080)


if __name__ == "__main__":
    unittest.main()