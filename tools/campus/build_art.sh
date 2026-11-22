#!/usr/bin/env bash
# Map v2 art, end to end (D46). From the repo root:
#
#   tools/campus/build_art.sh            # everything: buildings, infrastructure, trees, night windows, the campus
#   STAGES="infra trees post" tools/campus/build_art.sh
#
# Stages: buildings (author_campus_v2 + render all), infra (walls / parapets / balustrades), trees (species),
# post (night windows, import settings, regenerate the campus zone, Godot import). Logs: tools/.check-logs/art/.
set -u
cd "$(dirname "$0")/../.."
G="${GODOT:-/f/App Installers/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64_console.exe}"
LOG=tools/.check-logs/art
mkdir -p "$LOG"
ids() { (cd assets/source/blender/tools && python "$1" --list | tr -d '\r' | tr '\n' ' '); }

for stage in ${STAGES:-buildings infra courts trees post}; do
  case $stage in
    buildings)
      (cd assets/source/blender/tools && python author_campus_v2.py)
      python assets/source/blender/build_asset.py $(ids author_campus_v2.py) > "$LOG/buildings.log" 2>&1
      grep -E "batch:" "$LOG/buildings.log" | tail -1 ;;
    infra)
      (cd assets/source/blender/tools && python author_infra_v2.py)
      python assets/source/blender/build_asset.py $(ids author_infra_v2.py) > "$LOG/infra.log" 2>&1
      grep -E "batch:" "$LOG/infra.log" | tail -1 ;;
    courts)
      (cd assets/source/blender/tools && python author_courts_v2.py)
      python assets/source/blender/build_asset.py $(ids author_courts_v2.py) > "$LOG/courts.log" 2>&1
      grep -E "batch:" "$LOG/courts.log" | tail -1 ;;
    trees)
      python assets/source/blender/build_asset.py tree_rain tree_mahogany tree_mango tree_krishnachura palm_leaning palm_tall palm_areca > "$LOG/trees.log" 2>&1
      grep -E "batch:" "$LOG/trees.log" | tail -1 ;;
    post)
      python tools/campus/night_windows.py | tail -1
      python tools/campus/import_settings.py
      python tools/zones/campus_world.py > "$LOG/campus_world.log" 2>&1; grep -E "^campus:|registry:" "$LOG/campus_world.log"
      timeout 900 "$G" --headless --path . --import > "$LOG/import.log" 2>&1
      echo "godot import exit $?" ;;
    *) echo "unknown stage: $stage" ;;
  esac
done
