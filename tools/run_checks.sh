#!/usr/bin/env bash
# Runs the project's headless check suites and prints one summary line each (Docs/TESTING.md).
#
#   tools/run_checks.sh                 # every default suite
#   CHECKS="Movement Validator" tools/run_checks.sh
#   CHECKS="Chapter1 Chapter2 Chapter3 Chapter4 Chapter5 DebugKeys Campus" tools/run_checks.sh   # parked story suites (D45)
#   tools/run_checks.sh mylabel         # logs under tools/.check-logs/mylabel/
#
# Environment: CHECKS (suites to run), TMO (per-suite timeout, seconds), VARGS (extra validator args, e.g.
# --self-test or --dump-baseline), GODOT (the executable).
set -u
cd "$(dirname "$0")/.."
G="${GODOT:-/f/App Installers/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64_console.exe}"
OUT="tools/.check-logs/${1:-run}"
mkdir -p "$OUT"
fails=0

run() { # name scene args...
  local name=$1 scene=$2; shift 2
  timeout "${TMO:-900}" "$G" --headless --path . "$scene" "$@" > "$OUT/$name.log" 2>&1; local ec=$?
  local res; res=$(grep -E '\] (PASS|FAIL)' "$OUT/$name.log" | tail -1 | sed 's/^ *//')
  local errs; errs=$(grep -cE '^(ERROR|SCRIPT ERROR|WARNING)' "$OUT/$name.log")
  [ "$ec" -ne 0 ] && fails=$((fails + 1))
  printf '%-14s exit=%s  err/warn-lines=%-3s %s\n' "$name" "$ec" "$errs" "$res"
}

# The story (Chapters 1-5) is parked while the campus is rebuilt from the official board (Map v2, D45): its suites
# drive the retired exterior zones, so they are not run by default. They come back when the story is re-fitted.
LEGACY="Chapter1 Chapter2 Chapter3 Chapter4 Chapter5 DebugKeys Campus"
DEFAULT="Scripts Validator GameSession Character Movement Audio Camera Transition Occlusion Interaction CampusWorld"

for c in ${CHECKS:-$DEFAULT}; do
  case $c in
    Scripts)     run Scripts     res://scenes/tests/scripts/ScriptCompileCheck.tscn ;;
    Validator)   run Validator   res://scenes/tests/zone_validation/ZoneValidator.tscn -- --quit-after-checks ${VARGS:-} ;;
    GameSession) run GameSession res://scenes/tests/zone_validation/GameSessionCheck.tscn -- --quit-after-checks ;;
    Character)   run Character   res://scenes/tests/character_previews/PlayerCharacterCheck.tscn -- --quit-after-checks ;;
    Movement)    run Movement    res://scenes/tests/feel/MovementCheck.tscn -- --quit-after-checks ;;
    Audio)       run Audio       res://scenes/tests/feel/AudioCheck.tscn -- --quit-after-checks ;;
    Camera)      run Camera      res://scenes/tests/feel/CameraCheck.tscn -- --quit-after-checks ;;
    Transition)  run Transition  res://scenes/tests/feel/TransitionCheck.tscn -- --quit-after-checks ;;
    Occlusion)   run Occlusion   res://scenes/tests/feel/OcclusionCheck.tscn -- --quit-after-checks ;;
    Interaction) run Interaction res://scenes/tests/feel/InteractionCheck.tscn -- --quit-after-checks ;;
    Chapter1)    run Chapter1    res://scenes/tests/story/Chapter1Check.tscn -- --quit-after-checks ;;
    Chapter2)    run Chapter2    res://scenes/tests/story/Chapter2Check.tscn -- --quit-after-checks ;;
    Chapter3)    run Chapter3    res://scenes/tests/story/Chapter3Check.tscn -- --quit-after-checks ;;
    Chapter4)    run Chapter4    res://scenes/tests/story/Chapter4Check.tscn -- --quit-after-checks ;;
    Chapter5)    run Chapter5    res://scenes/tests/story/Chapter5Check.tscn -- --quit-after-checks ;;
    DebugKeys)   run DebugKeys   res://scenes/tests/story/DebugKeysCheck.tscn -- --quit-after-checks ;;
    Campus)      run Campus      res://scenes/tests/story/CampusTraversalCheck.tscn -- --quit-after-checks ;;
    CampusWorld) run CampusWorld res://scenes/tests/zone_validation/CampusWorldCheck.tscn -- --quit-after-checks ;;
    *)           echo "unknown suite: $c" ;;
  esac
done
echo "logs: $OUT"
exit $((fails > 0))
