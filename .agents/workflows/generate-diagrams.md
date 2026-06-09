# Workflow: Generate All Diagrams

**Trigger:** Invoked by `master-sync.md` Phase 4, or manually via `/ask run @[.agents/workflows/generate-diagrams.md]`

## Objective
A generalized, universal pipeline to scan the project for any programmatic diagram definitions (D2 or Python), compile them into structured images, and autonomously apply the Strict AI Styling Pass to guarantee aesthetic quality without spelling hallucinations.

## Execution Steps

### Phase 1: Diagram Discovery
1. Scan the `docs/` folder (and any subfolders) for all `.d2` and `.py` diagram definition files.
2. For each identified diagram file, extract the base `<diagram_name>` (e.g., `handover_flow.d2` -> `handover_flow`).

### Phase 2: Generate Technical Diagrams
1. Iterate through the discovered `.d2` files. Run `d2 docs/<diagram_name>.d2 docs/assets/<diagram_name>_technical.png --theme=200 --sketch`.
2. Iterate through any discovered `.py` diagram files. Run `python docs/<diagram_name>.py` (Output must be configured to generate `docs/assets/<diagram_name>_technical.png`).
3. Verify that all base `<diagram_name>_technical.png` files exist and are non-zero bytes.

### Phase 3: The Showcase Styling Pass
1. Per the `.agents/skills/diagram-generator/SKILL.md` rules, iterate through the list of generated `_technical.png` files.
2. For each diagram, read its `.d2` or `.py` source to extract every node label, cluster name, and edge label.
3. Call `generate_image` with `docs/assets/<diagram_name>_technical.png` in `ImagePaths` as the structural content base.
4. Use the exact prompt template from `SKILL.md` to generate the AI-styled background.
5. Save the AI-styled output as `docs/assets/<diagram_name>_showcase.png`.

### Phase 4: Composite Generation & Cleanup
1. Execute `python docs/composite_diagram.py docs/assets/<diagram_name>_technical.png docs/assets/<diagram_name>_showcase.png docs/assets/<diagram_name>.png`.
2. Delete the intermediate `_technical.png` and `_showcase.png` files to maintain strict 10MB limits and avoid asset bloat.
3. Ensure `README.md` correctly references the final `<diagram_name>.png`.
