# Handsfree-Chords Justfile

list:
    @just -l

# Avvia il server web per il live stage player in foreground
run:
    python3 app/server.py

# Compila la versione statica per GitHub Pages in docs/
build:
    python3 scripts/build_ghp.py

# Compila, testa, pusha e forza il deploy su GitHub Pages (che altrimenti è pigro!)
deploy: build test
    git push origin main
    gh api -X POST repos/palladius/handsfree-chords/pages/builds
    @echo "🚀 Build GitHub Pages richiesto! Verifica stato con: gh run list -L 3"

# Valida tutti gli spartiti nella cartella songs/ e lancia gli unit test
test:
    @echo "🧪 Validazione spartiti in songs/..."
    python3 -c "import glob, os, sys; [os.system(f'python3 scripts/validate_spartito.py \"{f}\"') for f in sorted(glob.glob('songs/*.md'))]"
    @echo "🧪 Esecuzione unit test..."
    python3 -m unittest discover -s tests
