# Photos Directory

Place your photography here to generate your portfolio site.

## Organization

- **Flat structure:** All photos in this directory will appear in a single gallery
- **Albums:** Create subdirectories for different albums/categories
  - Example: `photos/wildlife/`, `photos/portraits/`, `photos/landscapes/`
  - Subdirectory names will become album titles

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)

## Usage

1. Add your photos to this directory (or create a symlink to your photo library)
2. Run `python build.py` to generate the static site
3. Output will be in `docs/` directory

## Tips

- Use high-resolution images; the build script will generate optimized versions
- Organize by subdirectory for automatic album categorization
- File names don't matter—images will be sorted by metadata/name
