#!/usr/bin/env python3
"""
Photfolio Build Script
Generates a static photography portfolio site from photos/ directory
"""

import os
import shutil
import yaml
from pathlib import Path
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict


class PhotfolioBuilder:
    def __init__(self, config_path="config.yaml"):
        """Initialize builder with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.photos_dir = Path("photos")
        self.build_dir = Path("build")
        self.templates_dir = Path("templates")
        self.styles_dir = Path("styles")

        # Image output directories
        self.images_dir = self.build_dir / "images"
        self.thumbs_dir = self.build_dir / "images" / "thumbs"

        # Setup Jinja2 templating
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def clean_build(self):
        """Remove existing build directory"""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir()
        self.images_dir.mkdir(parents=True)
        self.thumbs_dir.mkdir()

    def scan_photos(self):
        """
        Scan photos/ directory and organize into albums
        Returns: dict of {album_name: [photo_paths]}
        """
        albums = defaultdict(list)
        extensions = tuple(self.config['advanced']['image_extensions'])

        # Check if photos directory exists
        if not self.photos_dir.exists():
            print(f"Warning: {self.photos_dir} does not exist")
            return albums

        # Scan for photos
        for item in sorted(self.photos_dir.rglob("*")):
            if item.is_file() and item.suffix.lower() in extensions:
                # Skip README files
                if item.name == "README.md":
                    continue

                # Determine album name
                relative = item.relative_to(self.photos_dir)
                if len(relative.parts) > 1:
                    # Photo is in subdirectory - use as album name
                    album_name = relative.parts[0]
                else:
                    # Photo is in root - use "Main" album
                    album_name = "Main"

                albums[album_name].append(item)

        return dict(albums)

    def process_image(self, source_path, album_name, photo_index=1):
        """
        Process a single image: resize, optimize, strip EXIF
        Returns: dict with image info for template
        """
        # Generate output filename based on config
        if self.config['portfolio']['keep_original_filenames']:
            filename = source_path.name
            stem = source_path.stem
        else:
            # Use sequential numbering
            extension = source_path.suffix
            stem = f"photo-{photo_index:03d}"
            filename = stem + extension

        # Create album subdirectory in build
        album_dir = self.images_dir / album_name
        album_thumbs_dir = self.thumbs_dir / album_name
        album_dir.mkdir(exist_ok=True)
        album_thumbs_dir.mkdir(exist_ok=True)

        full_path = album_dir / filename
        thumb_path = album_thumbs_dir / filename

        # Open and process image
        with Image.open(source_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background

            # Strip EXIF if configured
            exif_data = None
            if not self.config['metadata']['strip_exif'] and self.config['metadata']['display_exif']:
                exif_data = img.getexif()

            # Resize full image if needed
            max_width = self.config['portfolio']['max_image_width']
            max_height = self.config['portfolio']['max_image_height']

            full_img = img.copy()
            full_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Save full image
            save_kwargs = {'quality': 95, 'optimize': True}
            if self.config['advanced']['progressive_jpeg']:
                save_kwargs['progressive'] = True

            full_img.save(full_path, **save_kwargs)

            # Generate thumbnail
            thumb_img = img.copy()
            thumb_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            thumb_img.save(
                thumb_path,
                quality=self.config['portfolio']['thumbnail_quality'],
                optimize=True
            )

            # Generate WebP versions if enabled
            webp_full_path = None
            webp_thumb_path = None
            if self.config['portfolio']['generate_webp']:
                webp_full_path = album_dir / f"{stem}.webp"
                webp_thumb_path = album_thumbs_dir / f"{stem}.webp"

                full_img.save(webp_full_path, 'WEBP', quality=90)
                thumb_img.save(webp_thumb_path, 'WEBP', quality=80)

        # Build image info dictionary
        img_info = {
            'filename': filename,
            'full': f"images/{album_name}/{filename}",
            'thumb': f"images/thumbs/{album_name}/{filename}",
            'width': full_img.width,
            'height': full_img.height,
            'exif': exif_data
        }

        if webp_full_path:
            img_info['full_webp'] = f"images/{album_name}/{stem}.webp"
            img_info['thumb_webp'] = f"images/thumbs/{album_name}/{stem}.webp"

        return img_info

    def generate_html(self, albums_data):
        """Generate HTML pages from templates"""
        # Copy CSS files
        css_dest = self.build_dir / "styles"
        if self.styles_dir.exists():
            shutil.copytree(self.styles_dir, css_dest)

        # Copy assets directory (favicon, etc.)
        assets_dir = Path("assets")
        assets_dest = self.build_dir / "assets"
        if assets_dir.exists():
            shutil.copytree(assets_dir, assets_dest)

        # Render index page (all albums)
        template = self.env.get_template('index.html')
        html = template.render(
            config=self.config,
            albums=albums_data
        )

        with open(self.build_dir / 'index.html', 'w') as f:
            f.write(html)

        # Render individual album pages
        album_template = self.env.get_template('album.html')
        for album_name, photos in albums_data.items():
            html = album_template.render(
                config=self.config,
                album_name=album_name,
                photos=photos,
                all_albums=list(albums_data.keys())
            )

            album_file = self.build_dir / f"{album_name.lower().replace(' ', '-')}.html"
            with open(album_file, 'w') as f:
                f.write(html)

    def build(self):
        """Main build process"""
        print("Starting Photfolio build...")

        # Clean and prepare build directory
        print("Cleaning build directory...")
        self.clean_build()

        # Scan for photos
        print("Scanning photos...")
        albums = self.scan_photos()

        if not albums:
            print("No photos found! Add images to the photos/ directory.")
            return

        print(f"Found {len(albums)} album(s):")
        for album, photos in albums.items():
            print(f"  - {album}: {len(photos)} photo(s)")

        # Process images
        print("\nProcessing images...")
        albums_data = {}

        for album_name, photo_paths in albums.items():
            print(f"Processing album '{album_name}'...")
            albums_data[album_name] = []

            for idx, photo_path in enumerate(photo_paths, start=1):
                print(f"  - {photo_path.name}")
                img_info = self.process_image(photo_path, album_name, photo_index=idx)
                albums_data[album_name].append(img_info)

        # Generate HTML
        print("\nGenerating HTML...")
        self.generate_html(albums_data)

        print(f"\n✓ Build complete! Site generated in {self.build_dir}/")
        print(f"  Open {self.build_dir}/index.html in your browser to view.")


if __name__ == "__main__":
    builder = PhotfolioBuilder()
    builder.build()
