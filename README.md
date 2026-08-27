# AML-Detective

A text-based game about a detective in the AML/KYC space who solves AML-related financial crimes.

## Run the game

```bash
python aml_detective_game.py
```

## Update game requirements/content

The game is driven by `/home/runner/work/AML-Detective/AML-Detective/game_content.json`.

To update scenarios, choices, or outcomes, edit that JSON document and rerun:

```bash
python aml_detective_game.py --content-file game_content.json
```

This lets you raise follow-up requests and evolve the game content without changing core game code.

## Run tests

```bash
python -m unittest tests/test_aml_detective_game.py -v
```
