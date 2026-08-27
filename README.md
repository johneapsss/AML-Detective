# AML-Detective

A text-based AML/KYC detective game where you investigate financial-crime alerts, gather evidence, and submit case conclusions.

## Run the game

```bash
python aml_detective_game.py
```

### Useful options

```bash
# start fresh and ignore prior saved state
python aml_detective_game.py --new-game

# use custom requirement/case file
python aml_detective_game.py --content-file game_content.json

# save progress to a specific file
python aml_detective_game.py --save-file game_progress.json
```

## Requirements/content architecture

The game engine is in `/home/runner/work/AML-Detective/AML-Detective/aml_detective_game.py` and case requirements are externalized in `/home/runner/work/AML-Detective/AML-Detective/game_content.json`.

The current MVP content reflects the attached requirement set with:
- 3 difficulty levels (easy, intermediate, advanced)
- resource tracking (time, budget, energy)
- experience score and rank progression
- evidence attributes and multiple outcomes per case
- educational disclaimer for a Singapore-focused fictional context

Add or revise case files by editing `game_content.json` without rewriting the engine.

## Run tests

```bash
python -m unittest tests/test_aml_detective_game.py -v
```
