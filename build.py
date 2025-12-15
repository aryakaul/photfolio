#!/usr/bin/env python3
"""
Photfolio Build Script
Generates a static photography portfolio site from photos/ directory
"""

import os
import shutil
import yaml
from pathlib import Path
from datetime import datetime
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict


class PhotfolioBuilder:
    def __init__(self, config_path="config.yaml"):
        """Initialize builder with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Get configurable directories from config, with defaults
        self.photos_dir = Path(self.config.get('directories', {}).get('source', 'photos'))
        self.build_dir = Path(self.config.get('directories', {}).get('target', 'docs'))

        # Image output directory (can be separate from build_dir)
        images_config = self.config.get('directories', {}).get('images', '')
        if images_config:
            # User specified a separate images directory
            self.images_output_dir = Path(images_config)
        else:
            # Default: images go in build_dir/images
            self.images_output_dir = self.build_dir / "images"

        # Base path for images in HTML (URL path, not filesystem)
        self.images_base_path = self.config.get('site', {}).get('images_base_path', 'images')

        # Keep these hardcoded (part of codebase)
        self.templates_dir = Path("templates")
        self.styles_dir = Path("styles")

        # Image output directories (physical filesystem paths)
        self.images_dir = self.images_output_dir
        self.thumbs_dir = self.images_output_dir / "thumbs"

        # Setup Jinja2 templating
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def clean_build(self, incremental=False):
        """Remove existing build and image directories

        Args:
            incremental: If True, preserve image outputs (skip image deletion)
        """
        # Clean HTML/CSS build directory
        if self.build_dir.exists():
            # In incremental mode, preserve images subdirectory
            if incremental and (self.build_dir / "images").exists():
                # Remove everything except images
                for item in self.build_dir.iterdir():
                    if item.name != "images":
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
            else:
                # Full clean
                shutil.rmtree(self.build_dir)

        self.build_dir.mkdir(parents=True, exist_ok=True)

        # Handle separate images directory
        if not incremental:
            if self.images_output_dir != self.build_dir / "images":
                # Separate images directory - clean it independently
                if self.images_dir.exists():
                    shutil.rmtree(self.images_dir)

        # Create image directories (idempotent)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

    def scan_photos(self):
        """
        Scan photos/ directory and organize into nested album structure
        Returns: dict of nested albums (or special single-album structure)
        """
        albums = {}
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

                relative = item.relative_to(self.photos_dir)
                self._add_photo_to_nested_structure(albums, relative, item)

        # Special case: if ONLY root photos exist (no subdirectory albums),
        # convert "Main" album to a single-album portfolio
        if len(albums) == 1 and 'Main' in albums:
            # Return the Main album photos directly as a single-album structure
            return {'_single_album': True, 'photos': albums['Main']['photos']}

        return albums

    def _add_photo_to_nested_structure(self, albums, relative_path, photo_path):
        """Recursively add photo to nested album structure"""
        if len(relative_path.parts) == 1:
            # Photo in root -> "Main" album
            if 'Main' not in albums:
                albums['Main'] = {'name': 'Main', 'path': 'main', 'photos': [], 'subalbums': {}}
            albums['Main']['photos'].append(photo_path)
        else:
            # Photo in subdirectory
            parts = relative_path.parts[:-1]  # All except filename
            current = albums
            path_so_far = []

            for part in parts:
                path_so_far.append(part)
                if part not in current:
                    current[part] = {
                        'name': part,
                        'path': '/'.join(path_so_far),
                        'photos': [],
                        'subalbums': {}
                    }
                if len(path_so_far) == len(parts):
                    # Final level - add photo here
                    current[part]['photos'].append(photo_path)
                else:
                    # Intermediate level - descend
                    current = current[part]['subalbums']

    def add_border_to_image(self, image, border_width):
        """
        Add white border to image using Pillow.

        Args:
            image: PIL Image object
            border_width: Border width in pixels (0 = no border)

        Returns:
            PIL Image with border, or original image if border_width is 0
        """
        if border_width <= 0:
            return image

        try:
            from PIL import ImageOps
            # Add white border (RGB: 255, 255, 255)
            bordered = ImageOps.expand(image, border=border_width, fill=(255, 255, 255))
            return bordered
        except Exception as e:
            print(f"Warning: Failed to add border: {e}")
            print("Continuing without border...")
            return image

    def process_image(self, source_path, album_path, photo_index=1, skip_if_current=False):
        """
        Process a single image: resize, optimize, strip EXIF

        Args:
            source_path: Path to source photo
            album_path: Album path for output organization
            photo_index: Sequential index for numbering
            skip_if_current: If True, skip processing if outputs are up-to-date

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

        # Create nested album directory structure
        album_dir = self.images_dir / album_path
        album_thumbs_dir = self.thumbs_dir / album_path
        album_dir.mkdir(parents=True, exist_ok=True)
        album_thumbs_dir.mkdir(parents=True, exist_ok=True)

        full_path = album_dir / filename
        thumb_path = album_thumbs_dir / filename

        # Skip logic for incremental builds
        if skip_if_current:
            # Determine all expected output files
            outputs_to_check = [full_path, thumb_path]

            if self.config['portfolio']['generate_webp']:
                webp_full_path = album_dir / f"{stem}.webp"
                webp_thumb_path = album_thumbs_dir / f"{stem}.webp"
                outputs_to_check.extend([webp_full_path, webp_thumb_path])

            # Skip if ALL outputs exist AND are newer than source
            if self._should_skip_processing(source_path, outputs_to_check):
                # Return metadata without re-processing
                return self._build_image_info(
                    source_path, album_path, filename,
                    full_path, thumb_path,
                    webp_stem=stem if self.config['portfolio']['generate_webp'] else None
                )

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

            # Apply border if configured
            border_proportion = self.config['portfolio'].get('border_width', 0)
            if border_proportion > 0:
                with Image.open(full_path) as bordered_img:
                    # Calculate border as percentage of smaller dimension
                    border_px = int(min(bordered_img.width, bordered_img.height) * border_proportion)
                    bordered_img = self.add_border_to_image(bordered_img, border_px)
                    bordered_img.save(full_path, **save_kwargs)

            # Generate thumbnail
            thumb_img = img.copy()
            thumb_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            thumb_img.save(
                thumb_path,
                quality=self.config['portfolio']['thumbnail_quality'],
                optimize=True
            )

            # Apply border to thumbnail if configured
            if border_proportion > 0:
                with Image.open(thumb_path) as bordered_thumb:
                    # Calculate border as percentage of smaller dimension
                    border_px = int(min(bordered_thumb.width, bordered_thumb.height) * border_proportion)
                    bordered_thumb = self.add_border_to_image(bordered_thumb, border_px)
                    bordered_thumb.save(
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

                # Apply border to WebP versions if configured
                if border_proportion > 0:
                    with Image.open(webp_full_path) as bordered_webp:
                        # Calculate border as percentage of smaller dimension
                        border_px = int(min(bordered_webp.width, bordered_webp.height) * border_proportion)
                        bordered_webp = self.add_border_to_image(bordered_webp, border_px)
                        bordered_webp.save(webp_full_path, 'WEBP', quality=90)

                    with Image.open(webp_thumb_path) as bordered_webp_thumb:
                        # Calculate border as percentage of smaller dimension
                        border_px = int(min(bordered_webp_thumb.width, bordered_webp_thumb.height) * border_proportion)
                        bordered_webp_thumb = self.add_border_to_image(bordered_webp_thumb, border_px)
                        bordered_webp_thumb.save(webp_thumb_path, 'WEBP', quality=80)

        # Build image info dictionary with configurable base path
        # Ensure base path doesn't end with slash for consistency
        base_path = self.images_base_path.rstrip('/')

        img_info = {
            'filename': filename,
            'full': f"{base_path}/{album_path}/{filename}" if album_path else f"{base_path}/{filename}",
            'thumb': f"{base_path}/thumbs/{album_path}/{filename}" if album_path else f"{base_path}/thumbs/{filename}",
            'width': full_img.width,
            'height': full_img.height,
            'exif': exif_data
        }

        if webp_full_path:
            if album_path:
                img_info['full_webp'] = f"{base_path}/{album_path}/{stem}.webp"
                img_info['thumb_webp'] = f"{base_path}/thumbs/{album_path}/{stem}.webp"
            else:
                img_info['full_webp'] = f"{base_path}/{stem}.webp"
                img_info['thumb_webp'] = f"{base_path}/thumbs/{stem}.webp"

        return img_info

    def _should_skip_processing(self, source_path, output_paths):
        """
        Check if image processing can be skipped

        Args:
            source_path: Source image file path
            output_paths: List of expected output file paths

        Returns:
            True if all outputs exist and are newer than source, False otherwise
        """
        # Check all outputs exist
        if not all(p.exists() for p in output_paths):
            return False

        # Get source modification time
        source_mtime = source_path.stat().st_mtime

        # Check all outputs are newer than source
        for output_path in output_paths:
            if output_path.stat().st_mtime <= source_mtime:
                return False

        return True

    def _build_image_info(self, source_path, album_path, filename, full_path, thumb_path, webp_stem=None):
        """
        Build image metadata dictionary without re-processing
        Used when skipping processing in incremental builds

        Args:
            source_path: Original source image path
            album_path: Album path for URL generation
            filename: Output filename
            full_path: Path to full-size output
            thumb_path: Path to thumbnail output
            webp_stem: Stem for WebP files (if generated)

        Returns:
            Image info dictionary matching process_image() output
        """
        # Read dimensions from existing output (faster than re-opening source)
        with Image.open(full_path) as img:
            width, height = img.size

        # Build image info with configurable base path
        base_path = self.images_base_path.rstrip('/')
        stem = Path(filename).stem

        img_info = {
            'filename': filename,
            'full': f"{base_path}/{album_path}/{filename}" if album_path else f"{base_path}/{filename}",
            'thumb': f"{base_path}/thumbs/{album_path}/{filename}" if album_path else f"{base_path}/thumbs/{filename}",
            'width': width,
            'height': height,
            'exif': None  # EXIF already stripped in previous build
        }

        # Add WebP paths if they exist
        if webp_stem:
            album_dir = self.images_dir / album_path if album_path else self.images_dir
            webp_full_path = album_dir / f"{webp_stem}.webp"

            if webp_full_path.exists():
                if album_path:
                    img_info['full_webp'] = f"{base_path}/{album_path}/{webp_stem}.webp"
                    img_info['thumb_webp'] = f"{base_path}/thumbs/{album_path}/{webp_stem}.webp"
                else:
                    img_info['full_webp'] = f"{base_path}/{webp_stem}.webp"
                    img_info['thumb_webp'] = f"{base_path}/thumbs/{webp_stem}.webp"

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

        # Render index page (only top-level albums)
        template = self.env.get_template('index.html')
        html = template.render(
            config=self.config,
            albums=albums_data,
            now=datetime.now()
        )
        with open(self.build_dir / 'index.html', 'w') as f:
            f.write(html)

        # Only render album pages if we have multiple albums
        # (single-album portfolios show all photos on index.html)
        if not albums_data.get('_single_album'):
            self._render_album_pages(albums_data, albums_data)

    def _render_album_pages(self, current_level, all_albums):
        """Recursively generate HTML for each album"""
        album_template = self.env.get_template('album.html')

        for album_name, album_node in current_level.items():
            has_subalbums = bool(album_node['subalbums'])

            html = album_template.render(
                config=self.config,
                album_name=album_node['name'],
                album_path=album_node['path'],
                photos=album_node['photos'],
                total_photos=album_node.get('total_photos', len(album_node['photos'])),
                subalbums=album_node['subalbums'] if has_subalbums else None,
                breadcrumb=self._build_breadcrumb(album_node['path']),
                has_subalbums=has_subalbums,
                all_albums=all_albums,
                now=datetime.now()
            )

            # Write to file: travel/spain -> travel-spain.html
            album_slug = album_node['path'].lower().replace(' ', '-').replace('/', '-')
            album_file = self.build_dir / f"{album_slug}.html"
            with open(album_file, 'w') as f:
                f.write(html)

            # Recurse into subalbums
            if album_node['subalbums']:
                self._render_album_pages(album_node['subalbums'], all_albums)

    def _count_all_photos(self, album_node):
        """Recursively count all photos in album and sub-albums"""
        count = len(album_node.get('photos', []))

        for subalbum in album_node.get('subalbums', {}).values():
            count += self._count_all_photos(subalbum)

        return count

    def _get_first_photo(self, album_node):
        """Recursively get the first photo from album or sub-albums"""
        # If this album has photos, return the first one
        if album_node.get('photos') and len(album_node['photos']) > 0:
            return album_node['photos'][0]

        # Otherwise, check sub-albums
        for subalbum in album_node.get('subalbums', {}).values():
            first_photo = self._get_first_photo(subalbum)
            if first_photo:
                return first_photo

        return None

    def _build_breadcrumb(self, album_path):
        """Generate breadcrumb navigation chain"""
        breadcrumb = [{'name': 'Home', 'url': 'index.html'}]

        if album_path == 'main':
            # For main album, show Home (link) / Main (current)
            breadcrumb.append({'name': 'Main', 'url': 'main.html'})
            return breadcrumb

        parts = album_path.split('/')
        for i, part in enumerate(parts):
            path_slug = '-'.join(parts[:i+1]).lower().replace(' ', '-')
            breadcrumb.append({
                'name': part.capitalize(),
                'url': f"{path_slug}.html"
            })

        return breadcrumb

    def _process_albums_recursive(self, albums_node, parent_path="", incremental=False):
        """Recursively process all albums and sub-albums

        Args:
            albums_node: Dictionary of album data
            parent_path: Parent album path for nesting
            incremental: If True, skip processing for up-to-date images

        Returns:
            Processed album data structure
        """
        result = {}
        for album_name, album_info in albums_node.items():
            album_path = album_info['path']

            print(f"Processing album '{album_path}'...")
            processed_photos = []
            for idx, photo_path in enumerate(album_info['photos'], start=1):
                print(f"  - {photo_path.name}")
                img_info = self.process_image(
                    photo_path, album_path, photo_index=idx,
                    skip_if_current=incremental
                )
                processed_photos.append(img_info)

            # Process subalbums first
            processed_subalbums = self._process_albums_recursive(
                album_info['subalbums'],
                album_path,
                incremental=incremental
            ) if album_info['subalbums'] else {}

            # Build the album node
            album_node = {
                'name': album_name,
                'path': album_path,
                'photos': processed_photos,
                'subalbums': processed_subalbums
            }

            # Add total photo count (including subalbums) and cover photo
            album_node['total_photos'] = self._count_all_photos(album_node)
            album_node['cover_photo'] = self._get_first_photo(album_node)

            result[album_name] = album_node

        return result

    def build(self, force_rebuild=False):
        """Main build process

        Args:
            force_rebuild: If True, force full rebuild (ignore incremental settings)
        """
        print("Starting Photfolio build...")

        # Determine incremental mode
        incremental_config = self.config.get('build', {}).get('incremental', False)
        incremental = incremental_config and not force_rebuild

        if incremental:
            print("Using incremental build mode (use --force for full rebuild)")
        else:
            reason = "forced rebuild" if force_rebuild else "incremental builds disabled in config"
            print(f"Using full rebuild mode ({reason})")

        # Clean and prepare build directory
        print("Cleaning build directory...")
        self.clean_build(incremental=incremental)

        # Scan for photos
        print("Scanning photos...")
        albums = self.scan_photos()

        if not albums:
            print("No photos found! Add images to the photos/ directory.")
            return

        # Handle special case: single album (root photos only)
        if albums.get('_single_album'):
            print("\nProcessing single-album portfolio...")
            processed_photos = []
            for idx, photo_path in enumerate(albums['photos'], start=1):
                print(f"  - {photo_path.name}")
                img_info = self.process_image(
                    photo_path, '', photo_index=idx,
                    skip_if_current=incremental
                )
                processed_photos.append(img_info)

            albums_data = {'_single_album': True, 'photos': processed_photos}
        else:
            # Process images
            print("\nProcessing images...")
            albums_data = self._process_albums_recursive(albums, incremental=incremental)

        # Generate HTML
        print("\nGenerating HTML...")
        self.generate_html(albums_data)

        print(f"\n✓ Build complete! Site generated in {self.build_dir}/")
        print(f"  Open {self.build_dir}/index.html in your browser to view.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a static photography portfolio site"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force full rebuild (ignore incremental build settings)'
    )
    args = parser.parse_args()

    builder = PhotfolioBuilder()
    builder.build(force_rebuild=args.force)
