#!/bin/sh
set -e

# Navigate to repository root
cd "$(dirname "$0")"

# Setup configuration for geotext
cd geotext

if [ ! -f config.js ]; then
  cp config.example.js config.js
  echo "Created geotext/config.js. Please add your MAPBOX_ACCESS_TOKEN to this file."
else
  echo "geotext/config.js already exists."
fi

echo "Geotextr installation complete."
