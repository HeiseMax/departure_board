import os
import sys
import time
import re
import atexit
from shutil import get_terminal_size
from textwrap import shorten

from departure_data import fetch_departures


DEFAULT_REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "30"))

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
ANSI_HIDE_CURSOR = "\033[?25l"
ANSI_SHOW_CURSOR = "\033[?25h"
ANSI_HOME_CLEAR = "\033[H\033[J"
ANSI_FULL_CLEAR = "\033[2J\033[H"


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _ansi_fg(hex_color):
    red, green, blue = _hex_to_rgb(hex_color)
    return f"\033[38;2;{red};{green};{blue}m"


def _ansi_bg(hex_color):
    red, green, blue = _hex_to_rgb(hex_color)
    return f"\033[48;2;{red};{green};{blue}m"


def _ansi_wrap(text, fg=None, bg=None, bold=False, dim=False):
    parts = []
    if bold:
        parts.append(ANSI_BOLD)
    if dim:
        parts.append(ANSI_DIM)
    if fg:
        parts.append(_ansi_fg(fg))
    if bg:
        parts.append(_ansi_bg(bg))
    parts.append(str(text))
    parts.append(ANSI_RESET)
    return "".join(parts)


def _plain_width(value):
    return len(ANSI_RE.sub("", str(value)))


def _pad(value, width, align="left"):
    value = str(value)
    visible_width = _plain_width(value)
    if visible_width >= width:
        return value
    padding = width - visible_width
    if align == "right":
        return (" " * padding) + value
    if align == "center":
        left = padding // 2
        right = padding - left
        return (" " * left) + value + (" " * right)
    return value + (" " * padding)


def _fit_text(value, width):
    return shorten(str(value), width=width, placeholder="...") if width > 3 else str(value)[:width]


def _column_layout(board_width):
    line = 7
    track = 4
    in_col = 6
    planned = 14
    separators = 12  # 7 columns => 6 separators * 2 spaces

    remaining = max(24, board_width - (line + track + in_col + planned + separators))
    direction = max(18, min(50, int(remaining * 0.55)))
    station = max(14, min(24, int(remaining * 0.20)))
    stops = remaining - direction - station

    min_stops = 24
    if stops < min_stops:
        deficit = min_stops - stops
        shrink_direction = min(deficit, direction - 18)
        direction -= shrink_direction
        deficit -= shrink_direction

        if deficit > 0:
            shrink_station = min(deficit, station - 14)
            station -= shrink_station
            deficit -= shrink_station

        stops = remaining - direction - station

    return {
        "line": line,
        "direction": direction,
        "station": station,
        "track": track,
        "in": in_col,
        "planned": planned,
        "stops": max(min_stops, stops),
    }


def _wrap_segments(segments, width):
    if not segments:
        return [""]

    wrapped = []
    current = ""
    for segment in segments:
        segment = _fit_text(segment, width)
        piece = segment if not current else ", " + segment
        if len(current) + len(piece) > width:
            if current:
                wrapped.append(current)
                current = segment
            else:
                wrapped.append(segment)
                current = ""
        else:
            current += piece

    if current:
        wrapped.append(current)

    return wrapped or [""]


def clear_screen(stream=sys.stdout, full=False):
    # ANSI redraw is smoother than spawning cls/clear each refresh.
    sequence = ANSI_FULL_CLEAR if full else ANSI_HOME_CLEAR
    print(sequence, end="", file=stream, flush=True)


def hide_cursor(stream=sys.stdout):
    print(ANSI_HIDE_CURSOR, end="", file=stream, flush=True)


def show_cursor(stream=sys.stdout):
    print(ANSI_SHOW_CURSOR, end="", file=stream, flush=True)


def _status_color(departure):
    delay = departure.get("delay")
    if isinstance(delay, (int, float)) and delay > 0:
        return "#ef4444"
    return "#10b981"


def default_departure_renderer(departure, index=None, width=96):
    return render_departure_block(departure, index=index, width=width)


def render_departure_block(departure, index=None, width=96):
    layout = _column_layout(width)
    badge_text = _pad(departure["name"], 5, align="center")
    badge_style = departure.get("color", {"bg": "#334155", "fg": "#f8fafc"})
    badge = _ansi_wrap(badge_text, fg=f"#{badge_style['fg']}", bg=f"#{badge_style['bg']}", bold=True)
    direction_width = layout["direction"]
    station_width = layout["station"]
    direction = _fit_text(departure.get("direction", "N/A"), direction_width)
    station_label = departure.get("station_display_name") or departure.get("station", "N/A")
    station = _fit_text(station_label, station_width)
    track = departure.get("track", "N/A")
    if track == "N/A":
        track = "-"
    in_minutes = departure.get("time_to_departure", "N/A")
    planned = departure.get("scheduled_time", "N/A")
    delay = departure.get("delay", "N/A")

    planned_text = planned[:5] if planned != "N/A" else "N/A"
    delay_text = f"(+{delay:g})" if isinstance(delay, (int, float)) and delay > 0 else ""
    in_text = "Jetzt" if isinstance(in_minutes, int) and in_minutes <= 0 else (str(in_minutes) if in_minutes != "N/A" else "N/A")
    time_color = _status_color(departure)
    planned_rendered = _ansi_wrap(planned_text, fg=time_color, bold=True)
    in_rendered = _ansi_wrap(in_text, fg=time_color, bold=True)
    delay_rendered = _ansi_wrap(delay_text, fg=time_color, bold=True) if delay_text else ""

    def cell(text, cell_width, align="left"):
        return _pad(text, cell_width, align=align)

    first_line = (
        f"{cell(badge, layout['line'])}  "
        f"{cell(direction, direction_width)}  "
        f"{cell(station, station_width)}  "
        f"{cell(track, layout['track'], align='center')}  "
        f"{cell(in_rendered, layout['in'], align='right')}  "
        f"{cell(planned_rendered + delay_rendered, layout['planned'], align='left')}"
    )

    stops_at = departure.get("stops_at", {})
    stop_lines = [""]
    if stops_at:
        stop_parts = []
        for stop_name, stop_data in stops_at.items():
            arrival = stop_data.get("arrival_time", "N/A")
            stop_delay = stop_data.get("delay", "N/A")
            stop_delay_text = f" (+{stop_delay})" if isinstance(stop_delay, (int, float)) and stop_delay > 0 else ""
            stop_parts.append(f"{stop_name} ({arrival[:5]}){stop_delay_text}")

        stop_lines = _wrap_segments(stop_parts, layout["stops"])

    messages = departure.get("messages", [])
    # if messages:
    #     message_text = _fit_text(" | ".join(messages), layout["stops"])
        # stop_lines.append(_ansi_wrap(message_text, fg="#94a3b8", dim=True))
    #     # if messages:
    #     message_text = " | ".join(messages)
    #     lines.append(f"  {_ansi_wrap('Msg', fg='#94a3b8', bold=True)}: {_fit_text(message_text, width - 10)}")


    lines = []
    for idx, stop_line in enumerate(stop_lines):
        if idx == 0:
            lines.append(f"{first_line}  {cell(stop_line, layout['stops'])}")
        else:
            continued_line = (
                f"{cell('', layout['line'])}  "
                f"{cell('', direction_width)}  "
                f"{cell('', station_width)}  "
                f"{cell('', layout['track'], align='center')}  "
                f"{cell('', layout['in'], align='right')}  "
                f"{cell('', layout['planned'], align='left')}  "
                f"{cell(stop_line, layout['stops'])}"
            )
            lines.append(continued_line)

    return "\n".join(lines)


def print_departures(departures, render_departure=None, stream=sys.stdout, title=None, clear=True, width=96):
    render_departure = render_departure or default_departure_renderer

    if not hasattr(print_departures, "_last_frame_lines"):
        print_departures._last_frame_lines = 0

    term_size = get_terminal_size((width, 24))
    # Never exceed the real terminal width; wrapping causes apparent extra lines each refresh.
    term_width = max(40, term_size.columns)
    term_height = max(12, term_size.lines)
    board_width = max(30, term_width - 1)
    layout = _column_layout(board_width)

    lines = []

    def line(char="-"):
        lines.append(char * board_width)

    if clear and print_departures._last_frame_lines == 0:
        clear_screen(stream=stream, full=True)

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    header = title or "Bahn departures"
    _ = header
    lines.append(_pad(timestamp, board_width, align="center"))
    line("=")

    header_row = (
        f"{_pad('L', layout['line'], align='center')}  "
        f"{_pad('Nach', layout['direction'])}  "
        f"{_pad('Von', layout['station'])}  "
        f"{_pad('G', layout['track'], align='center')}  "
        f"{_pad('In', layout['in'], align='right')}  "
        f"{_pad('Um', layout['planned'])}  "
        f"{_pad('Stops', layout['stops'])}"
    )
    lines.append(_ansi_wrap(header_row, fg='#94a3b8', bold=True))
    line("-")

    if not departures:
        lines.append(_pad("No departures found.", board_width, align="center"))
    else:
        rendered_rows = []
        for index, departure in enumerate(departures, start=1):
            rendered_rows.extend(render_departure(departure, index=index, width=board_width).splitlines())
            if index != len(departures):
                rendered_rows.append("-" * board_width)

        static_lines = 4  # time, separator, header row, separator
        available_lines = max(3, term_height - static_lines)

        if len(rendered_rows) <= available_lines:
            lines.extend(rendered_rows)
        else:
            lines.extend(rendered_rows[:available_lines])
            hidden_lines = len(rendered_rows) - available_lines
            info = f"... {hidden_lines} more line(s) hidden; enlarge terminal to see all departures"
            # lines.append(_ansi_wrap(_fit_text(info, board_width), fg="#94a3b8", dim=True))

    # Ensure we overwrite leftover lines from the previous frame without a full clear.
    leftover = max(0, print_departures._last_frame_lines - len(lines))
    if leftover:
        lines.extend([" " * board_width] * leftover)

    frame = "\n".join(lines)
    stream.write("\033[H")
    stream.write(frame)
    stream.flush()

    print_departures._last_frame_lines = len(lines)


def run(refresh_seconds=DEFAULT_REFRESH_SECONDS, render_departure=None):
    hide_cursor()
    atexit.register(show_cursor)
    try:
        clear_screen(full=True)
        while True:
            try:
                departures = fetch_departures()
            except Exception as exc:
                message = _fit_text(f"Failed to fetch departures: {exc}", get_terminal_size((96, 24)).columns - 1)
                stream = sys.stdout
                stream.write("\033[H\033[J")
                stream.write(message)
                stream.flush()
            else:
                print_departures(departures, render_departure=render_departure, clear=False)

            time.sleep(refresh_seconds)
    finally:
        show_cursor()


if __name__ == "__main__":
    run()