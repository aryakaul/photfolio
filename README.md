# Photfolio

A minimal, performance-focused photography portfolio generator. Drop your photos in a folder, run a build script, and get a beautiful static website.

## Philosophy

- **Simple over complex**: Pure HTML/CSS, minimal dependencies
- **Fast over fancy**: Optimized images, lazy loading, modern formats
- **Modular over monolithic**: Easy to customize and extend
- **Static over dynamic**: No server-side processing, just fast file serving

## Features

- Auto-generates portfolio site from `photos/` directory
- Album support via subdirectories
- Responsive CSS Grid layout (mobile + desktop)
- Image optimization (thumbnails, resizing, WebP generation)
- EXIF stripping (configurable)
- Pure CSS lightbox (no JavaScript required)
- Lazy loading for performance
- GitHub Pages ready

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Your Photos

```bash
# Option A: Copy photos directly
cp -r /path/to/your/photos/* photos/

# Option B: Symlink to your photo library
ln -s /path/to/your/photos photos

# For albums, organize in subdirectories:
photos/
  wildlife/
    photo1.jpg
    photo2.jpg
  portraits/
    photo3.jpg
```

### 3. Configure

Edit `config.yaml` to customize your site:

```yaml
site:
  title: "Your Name Photography"
  author: "Your Name"
  description: "Your portfolio description"
  favicon: "favicon.png"  # Optional: add your icon to assets/
```

### 3.5. Add a Favicon (Optional)

Place your website icon in the `assets/` directory:

```bash
# Add your favicon to assets/
cp /path/to/your-icon.png assets/favicon.png
```

Supported formats: PNG, ICO, or SVG. If no favicon is provided, a default icon will be used.

### 4. Build

```bash
python build.py
```

### 5. Preview

Open `docs/index.html` in your browser, or serve locally:

```bash
cd docs
python -m http.server 8000
# Visit http://localhost:8000
```

## Configuration

See `config.yaml` for all options:

- **Site info**: Title, author, description, favicon
- **Portfolio settings**: Grid columns, image quality, max dimensions, filename handling
- **Metadata**: EXIF stripping and display options
- **Theme**: Colors, fonts
- **Footer**: Custom text, links
- **Albums**: Sorting, descriptions
- **Advanced**: Image formats, lazy loading, progressive JPEGs

### Footer Customization

Customize your footer via `config.yaml`:

**Basic copyright:**
```yaml
footer:
  text: "&copy; {year} {author}"
```
Output: `© 2025 Your Name`

**Custom text:**
```yaml
footer:
  text: "All rights reserved • {author} • {year}"
```
Output: `All rights reserved • Your Name • 2025`

**With social links:**
```yaml
footer:
  text: "&copy; {year} {author}"
  links:
    - label: "Instagram"  # Displays Instagram icon
      url: "https://instagram.com/yourhandle"
    - label: "Email"      # Displays email icon
      url: "mailto:your@email.com"
```

**Supported icon labels:** Links with labels "Instagram" or "Email" automatically render as icons instead of text. Other labels display as text.

**No footer:**
```yaml
footer:
  text: ""
```

Available variables: `{year}` (current year), `{author}` (from site.author)

## Deployment

### GitHub Pages

1. Build your site: `python build.py`
2. Copy `docs/` contents to your GitHub Pages repository
3. Commit and push

Or use GitHub Actions to automate the build process.

### Self-Hosted

1. Build your site: `python build.py`
2. Upload `docs/` directory to your web server
3. Point your domain to the directory

## Project Structure

```
photfolio/
├── photos/           # Source photos (add your images here)
├── assets/           # Static assets (favicon, logos, etc.)
├── docs/             # Generated site (git-ignored)
├── templates/        # HTML templates (Jinja2)
│   ├── index.html    # Main page / album grid
│   └── album.html    # Individual album view
├── styles/           # CSS stylesheets
│   └── main.css      # Main stylesheet
├── build.py          # Build script
├── config.yaml       # Configuration
└── requirements.txt  # Python dependencies
```

## How It Works

1. **Scan**: `build.py` scans `photos/` directory
2. **Organize**: Subdirectories become albums
3. **Process**: Generates thumbnails, resized images, WebP versions
4. **Optimize**: Strips EXIF (if configured), optimizes compression
5. **Generate**: Renders HTML from templates with image data
6. **Output**: Static site in `docs/` ready to deploy

## Performance

- **Modern image formats**: WebP with JPEG fallback
- **Responsive images**: Multiple sizes via `<picture>` element
- **Lazy loading**: Images load as user scrolls
- **Optimized compression**: Configurable quality settings
- **Progressive JPEGs**: Faster perceived load times
- **No JavaScript overhead**: Core functionality is pure CSS

## Customization

### Basic (Config File)

Edit `config.yaml` to change colors, fonts, and settings.

### Advanced (Templates)

Edit `templates/*.html` to modify layout and structure.

### Styling (CSS)

Edit `styles/main.css` to customize appearance. CSS variables in `:root` can be overridden.

## Requirements

- Python 3.8+
- Pillow (image processing)
- Jinja2 (templating)
- PyYAML (config parsing)

## License

Open source. Customize and use however you'd like.

## Roadmap

Future improvements (PRs welcome):

- [ ] Multiple theme presets
- [ ] Album descriptions from text files
- [ ] Custom sorting options (date, name, manual)
- [ ] Video support
- [ ] GitHub Actions workflow for automated builds
- [ ] EXIF display in lightbox
- [ ] Social media meta tags (Open Graph, Twitter Cards)
- [ ] Dark/light mode toggle

## Contributing

This is a personal project made open source. Feel free to fork, customize, and submit PRs for improvements.
