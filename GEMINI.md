# Gemini Instructions for handsfree-chords 🎹

## GitHub Pages (GHP) Build & Deploy Mandate
* **Pre-Commit Build (`just build`):** ALWAYS run `just build` and `just test` BEFORE running `git commit` and `git push`, so that `docs/index.html`, `docs/songs.json`, and `docs/songs_list.json` are freshly compiled and verified.
* **Force & Verify GHP Deploy (`just deploy`):** GitHub Pages has become lazy with automatic builds and deployments frequently stall or fail silently. Whenever pushing to `main`, ALWAYS run `just deploy` (or trigger `gh api -X POST repos/palladius/handsfree-chords/pages/builds` after `git push`) and verify that the GHP build succeeds and the live URL serves the updated bundle.
