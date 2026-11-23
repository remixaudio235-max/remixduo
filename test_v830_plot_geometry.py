"""V8.30: real chart geometry must survive vertical dock and toolbar changes."""
from types import SimpleNamespace
from plot_geometry_v7 import choose_canvas_pair,locate_plots

def test_actual_smaart_20261030_geometry():
    bounds=(0,0,1920,1040)
    rects=[(200,82,1720,537),(250,82,1696,498),
           (200,537,1720,992),(250,537,1696,953),
           (250,540,1696,748),(1,43,1919,1039)]
    rects+= [(250,82,1696,498)]*7+[(250,537,1696,953)]*7
    assert choose_canvas_pair(rects,bounds)==(
        (252,84,1442,412),(252,539,1442,412))

def test_known_good_previous_layout():
    # Older 9.6.4 chart coordinates before top toolbar changed.
    rects=[(250,110,1696,512),(250,551,1696,953)]
    assert choose_canvas_pair(rects,(0,0,1920,1040))==(
        (252,112,1442,398),(252,553,1442,398))

def test_window_movement_retains_screen_coordinate_mapping():
    dx,dy=320,45
    rects=[(250+dx,82+dy,1696+dx,498+dy),
           (250+dx,537+dy,1696+dx,953+dy)]
    result=choose_canvas_pair(rects,(dx,dy,1920+dx,1040+dy))
    assert result == ((252+dx,84+dy,1442,412),
                      (252+dx,539+dy,1442,412))

def test_unknown_single_or_overlapping_plot_fails_closed():
    bounds=(0,0,1920,1040)
    assert choose_canvas_pair([(250,82,1696,498)],bounds) is None
    assert choose_canvas_pair([(250,82,1696,498),(250,250,1696,700)],bounds) is None

def test_mismatched_horizontal_canvases_fail_closed():
    bounds=(0,0,1920,1040)
    assert choose_canvas_pair([(250,82,1696,498),(310,537,1600,953)],bounds) is None
