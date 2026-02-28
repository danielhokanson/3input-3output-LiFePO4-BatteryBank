# Solar Battery Build Spec — Interactive Site

Interactive design & build specification for a consolidated LiFePO4 battery system built from salvaged Solariver solar pump units.

**Rev 3.1** — 4S3P (12× Grade B cells), three-shell serviceable enclosure, Salt Lake City outdoor installation.

## Quick Deploy to GitHub Pages

```bash
# Clone this repo (or just push the files)
git init
git add .
git commit -m "Initial commit — solar build spec Rev 3.1"
git branch -M main
git remote add origin git@github.com:danielhokanson/solar-build-spec.git
git push -u origin main
```

Then in the GitHub repo:
1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/ (root)**
4. Click **Save**

Site will be live at `https://danielhokanson.github.io/solar-build-spec/` within a minute or two.

## Local Development

```bash
cd solar-build-spec
python3 -m http.server 8080
# Open http://localhost:8080
```

A local server is needed because the site fetches JSON data files via `fetch()`.

## Progress Tracking

Build progress (checkpoints, notes, measurements) is stored in your browser's `localStorage`. This means:
- Progress persists across browser sessions on the same device
- Progress does NOT sync between devices
- Use the **Export/Import** page to back up progress as a JSON file or transfer between devices

## Structure

```
solar-build-spec/
├── index.html          # Main shell
├── css/style.css       # Styling
├── js/app.js           # SPA router, rendering, progress tracking
├── data/
│   ├── spec.json       # Full specification content
│   └── progress.json   # Default progress template
└── README.md
```

## License

Specification content and site code for personal use.
