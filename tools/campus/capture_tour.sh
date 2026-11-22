#!/usr/bin/env bash
# Map v2 screenshot tour: the same views every time, by day and at night (needs a window, not --headless).
#
#   tools/campus/capture_tour.sh            # -> Docs/screenshots/map_v2/latest/
#   OUT=Docs/screenshots/map_v2/v3 tools/campus/capture_tour.sh
#
# Positions are campus px (metres x 32, metres y 20.576), always OUTSIDE every footprint and fade rect (a player
# standing inside one fades that building to 30%). zoom < 1.5 shows more of the buildings than play does.
set -u
cd "$(dirname "$0")/../.."
G="${GODOT:-/f/App Installers/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64_console.exe}"
OUT="${OUT:-Docs/screenshots/map_v2/latest}"
mkdir -p "$OUT"
W=$(cygpath -w "$PWD/$OUT" 2>/dev/null || echo "$PWD/$OUT")
SHOTS="gate@15040,5473,zoom=1.2"
SHOTS+=";courts@14464,3951,zoom=1.1"
SHOTS+=";cds_field@11680,2881,zoom=1.0"
SHOTS+=";mosque@8576,4074,zoom=1.0"
SHOTS+=";auditorium@7184,3704,zoom=0.85"
SHOTS+=";five_fundamentals@9984,4650,zoom=1.2"
SHOTS+=";halls_courtyard@11200,1070,zoom=1.0"
SHOTS+=";south_hall@11200,1955,zoom=1.0"
SHOTS+=";academic_1@7424,2181,zoom=1.0"
SHOTS+=";workshops@4544,1564,zoom=1.0"
SHOTS+=";woods@4000,3601,zoom=1.2"
SHOTS+=";female_hall@1984,5391,zoom=1.0"
SHOTS+=";construction@1856,1070,zoom=0.9"
SHOTS+=";plaza_close@7680,2675,zoom=2.0"
SHOTS+=";workshop_roofs@4544,1564,zoom=1.6"
SHOTS+=";mosque_night@8576,4074,zoom=1.0,night,lantern"
SHOTS+=";halls_night@11200,1070,zoom=1.0,night,lantern"
SHOTS+=";gate_night@14912,5473,zoom=1.2,night,lantern"
timeout 600 "$G" --path . res://scenes/tests/environment_previews/ZoneCapture.tscn -- --out-dir="$W" --shots="$SHOTS" \
  > tools/.check-logs/capture_tour.log 2>&1
echo "capture exit $?"; grep -c "(OK)" tools/.check-logs/capture_tour.log; ls "$OUT"
