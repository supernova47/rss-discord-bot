from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
STYLE_SHEET = (PROJECT_DIR / "rssbot" / "static" / "style.css").read_text(encoding="utf-8")


def declarations_for(selector: str) -> str:
    rule = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", STYLE_SHEET)
    if rule is None:
        raise AssertionError(f"CSS rule not found for {selector}")
    return rule.group(1)


def font_size_for(selector: str) -> float:
    declaration = re.search(r"font-size:\s*([\d.]+)px", declarations_for(selector))
    if declaration is None:
        raise AssertionError(f"font-size declaration not found for {selector}")
    return float(declaration.group(1))


def color_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    luminances = sorted((color_luminance(foreground), color_luminance(background)), reverse=True)
    return (luminances[0] + 0.05) / (luminances[1] + 0.05)


def root_color(variable: str) -> str:
    declaration = re.search(rf"{re.escape(variable)}:\s*(#[\da-fA-F]{{6}})", declarations_for(":root"))
    if declaration is None:
        raise AssertionError(f"Color variable not found: {variable}")
    return declaration.group(1)


class ReadabilityStyleTests(unittest.TestCase):
    def test_feed_list_labels_and_statuses_are_at_least_eleven_pixels(self) -> None:
        for selector in (
            ".status-pill",
            ".feed-filter-field",
            ".feed-url",
            ".feed-meta",
            ".feed-error, .feed-error-hint, .feed-pending",
        ):
            with self.subTest(selector=selector):
                self.assertGreaterEqual(font_size_for(selector), 11)

    def test_form_and_preview_help_text_are_at_least_eleven_pixels(self) -> None:
        for selector in (
            ".field small",
            ".feed-discovery-copy span, .feed-discovery-copy small",
            ".preview-disclaimer",
            ".test-entry-copy small",
        ):
            with self.subTest(selector=selector):
                self.assertGreaterEqual(font_size_for(selector), 11)

    def test_quiet_text_has_readable_contrast_on_raised_surfaces(self) -> None:
        ratio = contrast_ratio(root_color("--quiet"), root_color("--surface-raised"))

        self.assertGreaterEqual(ratio, 4.5)


if __name__ == "__main__":
    unittest.main()
