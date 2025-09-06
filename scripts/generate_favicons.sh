#!/bin/bash
# Script to generate favicons and PWA icons from the Music Disciple logo

SOURCE_LOGO="/Users/sammontoya/christian cleanup windsurf/app/static/images/music-disciple-logo.png"
IMAGES_DIR="/Users/sammontoya/christian cleanup windsurf/app/static/images"

echo "🎵 Music Disciple Favicon Generator"
echo "=================================="

if [ ! -f "$SOURCE_LOGO" ]; then
    echo "❌ Logo not found at: $SOURCE_LOGO"
    echo "Please save your logo image as 'music-disciple-logo.png' in the images directory first."
    exit 1
fi

echo "✅ Found logo: $SOURCE_LOGO"

# Check if ImageMagick is available
if ! command -v convert &> /dev/null; then
    echo "⚠️  ImageMagick not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install imagemagick
    else
        echo "❌ Please install ImageMagick manually: brew install imagemagick"
        exit 1
    fi
fi

echo "🔄 Generating favicon sizes..."

# Generate favicons
convert "$SOURCE_LOGO" -resize 16x16 "$IMAGES_DIR/favicon-16x16.png"
convert "$SOURCE_LOGO" -resize 32x32 "$IMAGES_DIR/favicon-32x32.png"
convert "$SOURCE_LOGO" -resize 48x48 "$IMAGES_DIR/favicon.ico"

echo "🔄 Generating PWA icons..."

# Generate PWA icons
convert "$SOURCE_LOGO" -resize 72x72 "$IMAGES_DIR/icon-72x72.png"
convert "$SOURCE_LOGO" -resize 96x96 "$IMAGES_DIR/icon-96x96.png"
convert "$SOURCE_LOGO" -resize 114x114 "$IMAGES_DIR/icon-114x114.png"
convert "$SOURCE_LOGO" -resize 120x120 "$IMAGES_DIR/icon-120x120.png"
convert "$SOURCE_LOGO" -resize 128x128 "$IMAGES_DIR/icon-128x128.png"
convert "$SOURCE_LOGO" -resize 144x144 "$IMAGES_DIR/icon-144x144.png"
convert "$SOURCE_LOGO" -resize 152x152 "$IMAGES_DIR/icon-152x152.png"
convert "$SOURCE_LOGO" -resize 180x180 "$IMAGES_DIR/icon-180x180.png"
convert "$SOURCE_LOGO" -resize 192x192 "$IMAGES_DIR/icon-192x192.png"
convert "$SOURCE_LOGO" -resize 384x384 "$IMAGES_DIR/icon-384x384.png"
convert "$SOURCE_LOGO" -resize 512x512 "$IMAGES_DIR/icon-512x512.png"

echo "🔄 Generating navigation logo (32px height)..."
convert "$SOURCE_LOGO" -resize x32 "$IMAGES_DIR/music-disciple-logo-nav.png"

echo "✅ All icons generated successfully!"
echo ""
echo "📁 Generated files:"
ls -la "$IMAGES_DIR" | grep -E "(favicon|icon-|music-disciple)"
echo ""
echo "🚀 Restart the web container to see the new logo:"
echo "   docker compose restart web"
