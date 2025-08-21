#!/usr/bin/env node
/**
 * Build Script for Christian Music Curator
 *
 * This script orchestrates the frontend build process:
 * - Creates necessary directories
 * - Builds CSS and JavaScript assets
 * - Optimizes images (in production)
 * - Generates build manifest
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const isProduction = process.env.NODE_ENV === 'production';
const buildDir = path.join(__dirname, '..', 'app', 'static', 'dist');

console.log(`🚀 Starting ${isProduction ? 'production' : 'development'} build...`);

// Create build directories
const dirs = [
  path.join(buildDir, 'css'),
  path.join(buildDir, 'js'),
  path.join(buildDir, 'images')
];

dirs.forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`📁 Created directory: ${dir}`);
  }
});

try {
  // Build CSS
  console.log('🎨 Building CSS...');
  execSync('npm run build:css', { stdio: 'inherit' });

  // Build JavaScript
  console.log('📦 Building JavaScript...');
  const jsCommand = isProduction ? 'npm run build:js:prod' : 'npm run build:js:dev';
  execSync(jsCommand, { stdio: 'inherit' });

  // Optimize images in production
  if (isProduction) {
    console.log('🖼️  Optimizing images...');
    try {
      execSync('npm run optimize:images', { stdio: 'inherit' });
    } catch (error) {
      console.warn('⚠️  Image optimization failed (optional step):', error.message);
    }
  }

  // Generate build manifest
  const manifest = {
    buildTime: new Date().toISOString(),
    environment: isProduction ? 'production' : 'development',
    version: require('../package.json').version,
    assets: {
      css: [
        'dist/css/base.css',
        'dist/css/components.css',
        'dist/css/utilities.css'
      ],
      js: [
        'dist/js/main.js'
      ]
    }
  };

  fs.writeFileSync(
    path.join(buildDir, 'manifest.json'),
    JSON.stringify(manifest, null, 2)
  );

  console.log('✅ Build completed successfully!');
  console.log(`📋 Build manifest: ${path.join(buildDir, 'manifest.json')}`);

} catch (error) {
  console.error('❌ Build failed:', error.message);
  process.exit(1);
}
